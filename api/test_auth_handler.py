#!/usr/bin/env python3
"""
Test script for the enhanced AuthenticationHandler with JWT parsing and caching.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import jwt

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_handler import AuthenticationHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_mock_jwt_token(exp_minutes_from_now=60):
    """Create a mock JWT token with specified expiration"""
    exp_time = datetime.utcnow() + timedelta(minutes=exp_minutes_from_now)
    exp_timestamp = int(exp_time.timestamp())
    
    payload = {
        'iss': 'https://accounts.google.com',
        'aud': 'test-audience',
        'sub': 'test-subject',
        'exp': exp_timestamp,
        'iat': int(datetime.utcnow().timestamp()),
    }
    
    # Create JWT without signing (for testing purposes)
    token = jwt.encode(payload, 'secret', algorithm='HS256')
    logger.info(f"Created mock JWT token expiring at: {exp_time}")
    return token


def test_jwt_parsing():
    """Test JWT parsing functionality"""
    logger.info("=== Testing JWT Parsing ===")
    
    # Create AuthenticationHandler instance
    auth_handler = AuthenticationHandler()
    
    # Test with valid JWT token
    test_token = create_mock_jwt_token(60)  # Expires in 60 minutes
    expiry = auth_handler._parse_jwt_expiry(test_token)
    
    if expiry:
        logger.info(f"✅ Successfully parsed JWT expiry: {expiry}")
        time_to_expiry = expiry - datetime.utcnow()
        logger.info(f"✅ Time to expiry: {time_to_expiry.total_seconds():.1f} seconds")
    else:
        logger.error("❌ Failed to parse JWT expiry")
        return False
    
    # Test with expired token
    expired_token = create_mock_jwt_token(-60)  # Expired 60 minutes ago
    expired_expiry = auth_handler._parse_jwt_expiry(expired_token)
    
    if expired_expiry:
        logger.info(f"✅ Successfully parsed expired JWT expiry: {expired_expiry}")
        time_to_expiry = expired_expiry - datetime.utcnow()
        logger.info(f"✅ Time to expiry (negative): {time_to_expiry.total_seconds():.1f} seconds")
    else:
        logger.error("❌ Failed to parse expired JWT expiry")
        return False
    
    # Test with invalid token
    invalid_expiry = auth_handler._parse_jwt_expiry("invalid.jwt.token")
    if invalid_expiry is None:
        logger.info("✅ Correctly handled invalid JWT token")
    else:
        logger.error("❌ Should have returned None for invalid JWT token")
        return False
    
    return True


def test_token_expiry_caching():
    """Test token expiry caching mechanism"""
    logger.info("=== Testing Token Expiry Caching ===")
    
    auth_handler = AuthenticationHandler()
    
    # Create a mock credentials object with token but no expiry
    class MockCredentials:
        def __init__(self, token):
            self.token = token
            self.expiry = None  # Simulate credentials without expiry info
            self.valid = True
    
    # Test caching behavior
    test_token = create_mock_jwt_token(30)  # Expires in 30 minutes
    auth_handler._credentials = MockCredentials(test_token)
    
    # First call should parse and cache
    logger.info("First call to _get_token_expiry (should parse JWT):")
    expiry1 = auth_handler._get_token_expiry()
    
    # Second call should use cache
    logger.info("Second call to _get_token_expiry (should use cache):")
    expiry2 = auth_handler._get_token_expiry()
    
    if expiry1 and expiry2 and expiry1 == expiry2:
        logger.info("✅ Token expiry caching working correctly")
        logger.info(f"✅ Cached expiry: {expiry1}")
    else:
        logger.error("❌ Token expiry caching not working")
        return False
    
    # Test cache invalidation with new token
    new_token = create_mock_jwt_token(90)  # Different expiry
    auth_handler._credentials = MockCredentials(new_token)
    
    logger.info("Third call with new token (should parse new JWT):")
    expiry3 = auth_handler._get_token_expiry()
    
    if expiry3 and expiry3 != expiry1:
        logger.info("✅ Cache invalidation working correctly")
        logger.info(f"✅ New cached expiry: {expiry3}")
    else:
        logger.error("❌ Cache invalidation not working")
        return False
    
    return True


def test_expiration_detection():
    """Test token expiration detection logic"""
    logger.info("=== Testing Token Expiration Detection ===")
    
    auth_handler = AuthenticationHandler()
    
    class MockCredentials:
        def __init__(self, token, valid=True):
            self.token = token
            self.expiry = None
            self.valid = valid
    
    # Test with token expiring soon (should be detected as needing refresh)
    soon_expired_token = create_mock_jwt_token(0.5)  # Expires in 30 seconds
    auth_handler._credentials = MockCredentials(soon_expired_token)
    
    is_expiring = auth_handler._is_token_expired_or_expiring_soon()
    if is_expiring:
        logger.info("✅ Correctly detected token expiring soon")
    else:
        logger.error("❌ Failed to detect token expiring soon")
        return False
    
    # Test with token that has plenty of time left
    fresh_token = create_mock_jwt_token(120)  # Expires in 2 hours
    auth_handler._credentials = MockCredentials(fresh_token)
    
    is_expiring = auth_handler._is_token_expired_or_expiring_soon()
    if not is_expiring:
        logger.info("✅ Correctly identified fresh token as not needing refresh")
    else:
        logger.error("❌ Fresh token incorrectly flagged as needing refresh")
        return False
    
    # Test with already expired token
    expired_token = create_mock_jwt_token(-60)  # Expired 1 hour ago
    auth_handler._credentials = MockCredentials(expired_token)
    
    is_expiring = auth_handler._is_token_expired_or_expiring_soon()
    if is_expiring:
        logger.info("✅ Correctly detected expired token")
    else:
        logger.error("❌ Failed to detect expired token")
        return False
    
    return True


def main():
    """Run all tests"""
    logger.info("Starting AuthenticationHandler tests...")
    
    tests = [
        ("JWT Parsing", test_jwt_parsing),
        ("Token Expiry Caching", test_token_expiry_caching),
        ("Expiration Detection", test_expiration_detection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        logger.info("-" * 50)
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    logger.info(f"\n=== TEST SUMMARY ===")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! The enhanced auth_handler is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())