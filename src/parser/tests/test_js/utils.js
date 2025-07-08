// Utility functions
export const logger = {
    log: (message) => console.log(`[LOG] ${message}`),
    error: (message) => console.error(`[ERROR] ${message}`)
};

export function formatDate(date) {
    return date.toISOString();
}

module.exports = {
    logger,
    formatDate
};