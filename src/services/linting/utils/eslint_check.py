import subprocess
from loguru import logger


def check_and_install_eslint() -> None:
    """Check if ESLint is installed and install it globally if Node.js is available."""
    try:
        # First check if Node.js is installed
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.debug("Node.js not found, skipping ESLint check")
                return

            node_version = result.stdout.strip()
            logger.debug(f"Node.js found: {node_version}")

        except (
            FileNotFoundError,
            subprocess.SubprocessError,
        ):
            logger.debug("Node.js not found, skipping ESLint check")
            return

        # Check if ESLint is already installed globally
        try:
            result = subprocess.run(
                ["eslint", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                eslint_version = result.stdout.strip()
                logger.debug(f"ESLint already installed: {eslint_version}")
                return

        except (
            FileNotFoundError,
            subprocess.SubprocessError,
        ):
            # ESLint not found, proceed with installation
            pass

        # Install ESLint globally
        print("ESLint not found. Installing ESLint globally...")
        print("   This will help with JavaScript/TypeScript code analysis.")

        try:
            result = subprocess.run(
                ["npm", "install", "-g", "eslint"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("ESLint installed successfully!")
                logger.info("ESLint installed globally via npm")
            else:
                logger.warning(f"ESLint installation failed: {result.stderr}")
                print(f"ESLint installation failed: {result.stderr}")

        except Exception as install_error:
            logger.warning(f"ESLint installation error: {install_error}")
            print(f"ESLint installation error: {install_error}")

    except Exception as e:
        logger.error(f"Error checking ESLint installation: {e}")
