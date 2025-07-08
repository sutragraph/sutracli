// Express.js Routes - demonstrates API endpoint definitions

const express = require('express');
const router = express.Router();
const app = express();

// User routes
app.get('/api/users', (req, res) => {
    res.json({ users: [] });
});

app.get('/api/users/:id', (req, res) => {
    const userId = req.params.id;
    res.json({ id: userId, name: 'John Doe' });
});

app.post('/api/users', (req, res) => {
    const userData = req.body;
    res.status(201).json({ id: 123, ...userData });
});

app.put('/api/users/:id', (req, res) => {
    const userId = req.params.id;
    const userData = req.body;
    res.json({ id: userId, ...userData });
});

app.delete('/api/users/:id', (req, res) => {
    const userId = req.params.id;
    res.status(204).send();
});

app.patch('/api/users/:id', (req, res) => {
    const userId = req.params.id;
    const partialData = req.body;
    res.json({ id: userId, ...partialData });
});

// Order routes
app.get('/api/orders', (req, res) => {
    res.json({ orders: [] });
});

app.post('/api/orders', (req, res) => {
    const orderData = req.body;
    res.status(201).json({ id: 456, status: 'created', ...orderData });
});

app.get('/api/orders/:id', (req, res) => {
    const orderId = req.params.id;
    res.json({ id: orderId, status: 'pending' });
});

app.put('/api/orders/:id/status', (req, res) => {
    const orderId = req.params.id;
    const { status } = req.body;
    res.json({ id: orderId, status });
});

// Product routes
app.get('/api/products', (req, res) => {
    res.json({ products: [] });
});

app.get('/api/products/:id', (req, res) => {
    const productId = req.params.id;
    res.json({ id: productId, name: 'Sample Product' });
});

app.get('/api/products/search', (req, res) => {
    const query = req.query.q;
    res.json({ query, results: [] });
});

// Payment routes
app.post('/api/payments/process', (req, res) => {
    const paymentData = req.body;
    res.json({ id: 789, status: 'processed', ...paymentData });
});

app.post('/api/payments/:id/refund', (req, res) => {
    const paymentId = req.params.id;
    res.json({ id: paymentId, status: 'refunded' });
});

// Analytics routes
app.post('/api/analytics/events', (req, res) => {
    const eventData = req.body;
    res.status(201).json({ recorded: true, ...eventData });
});

app.get('/api/analytics/reports', (req, res) => {
    const { start, end } = req.query;
    res.json({ start, end, data: [] });
});

// Notification routes
app.post('/api/notifications/send', (req, res) => {
    const notificationData = req.body;
    res.json({ sent: true, ...notificationData });
});

// Router-based routes
router.get('/profile', (req, res) => {
    res.json({ profile: 'user profile' });
});

router.post('/profile/update', (req, res) => {
    const profileData = req.body;
    res.json({ updated: true, ...profileData });
});

router.delete('/profile/delete', (req, res) => {
    res.status(204).send();
});

// Mount router
app.use('/api/user', router);

// Middleware that might make API calls
app.use('/api/auth', (req, res, next) => {
    // This middleware might make external API calls for authentication
    const token = req.headers.authorization;
    if (token) {
        // Simulate API call to auth service
        validateTokenWithAuthService(token)
            .then(() => next())
            .catch(() => res.status(401).json({ error: 'Unauthorized' }));
    } else {
        res.status(401).json({ error: 'No token provided' });
    }
});

// Function that makes API calls (used by middleware)
async function validateTokenWithAuthService(token) {
    const axios = require('axios');
    const response = await axios.post('/api/auth/validate', { token });
    return response.data.valid;
}

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

module.exports = { app, router };