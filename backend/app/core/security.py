from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from app.core.config import settings
import logging
import bcrypt as bcrypt_lib

logger = logging.getLogger(__name__)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using direct bcrypt.
    """
    try:
        # Handle password length limit (bcrypt limit is 72 bytes)
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Verify using direct bcrypt
        return bcrypt_lib.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password using direct bcrypt.
    """
    try:
        # Handle password length limit
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Hash using direct bcrypt with reasonable rounds (default is 12)
        hashed_bytes = bcrypt_lib.hashpw(password_bytes, bcrypt_lib.gensalt())
        return hashed_bytes.decode('utf-8')
    except Exception as e:
        logger.error(f"Password hashing failed: {e}")
        raise

def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def validate_sa_id(id_number: str) -> bool:
    """
    Validate South African ID number using Luhn algorithm
    SA ID format: YYMMDDSSSSCAZ
    - YYMMDD: Date of birth
    - SSSS: Sequence number
    - C: Citizenship (0=SA, 1=Other)
    - A: Race (obsolete but still in number)
    - Z: Check digit (Luhn algorithm)
    
    Returns: True if valid, False otherwise
    """
    # Basic validation
    if len(id_number) != 13 or not id_number.isdigit():
        return False
    
    # Validate date components
    if not _validate_sa_id_date(id_number):
        return False
    
    # Validate Luhn check digit
    return _validate_luhn_check_digit(id_number)

def _validate_sa_id_date(id_number: str) -> bool:
    """
    Validate the date portion of South African ID (YYMMDD)
    """
    try:
        year = int(id_number[0:2])
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        
        # Basic month validation
        if month < 1 or month > 12:
            return False
        
        # Basic day validation
        if day < 1 or day > 31:
            return False
        
        # More specific day validation for each month
        days_in_month = {
            1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
        }
        
        if day > days_in_month[month]:
            return False
        
        # February validation (considering leap years for 29 days)
        if month == 2 and day == 29:
            # For SA ID, we don't know the century, so we'll be lenient
            pass
            
        return True
        
    except (ValueError, KeyError):
        return False

def _validate_luhn_check_digit(id_number: str) -> bool:
    """
    Validate the check digit using Luhn algorithm (mod 10)
    
    Steps:
    1. Starting from the rightmost digit (excluding check digit), double every second digit
    2. If doubling results in a number > 9, add the digits of the product
    3. Sum all digits
    4. Check digit should make the total sum divisible by 10
    """
    try:
        # Convert string to list of integers
        digits = [int(d) for d in id_number]
        
        # The check digit is the last digit
        check_digit = digits[-1]
        
        # We need to process all digits except the check digit
        digits_to_process = digits[:-1]
        
        total = 0
        # Process from right to left (reverse the list for easier processing)
        reversed_digits = list(reversed(digits_to_process))
        
        for i, digit in enumerate(reversed_digits):
            if i % 2 == 0:  # Every second digit (starting from first in reversed list)
                doubled = digit * 2
                if doubled > 9:
                    # Add the digits of the doubled number (equivalent to subtracting 9)
                    total += doubled - 9
                else:
                    total += doubled
            else:
                total += digit
        
        # The total + check digit should be divisible by 10
        return (total + check_digit) % 10 == 0
        
    except (ValueError, IndexError):
        return False

def calculate_luhn_check_digit(number: str) -> int:
    """
    Calculate the Luhn check digit for a given number
    Useful for testing and verification
    """
    digits = [int(d) for d in number]
    
    # Double every second digit from the right
    total = 0
    reversed_digits = list(reversed(digits))
    
    for i, digit in enumerate(reversed_digits):
        if i % 2 == 0:
            doubled = digit * 2
            if doubled > 9:
                total += doubled - 9
            else:
                total += doubled
        else:
            total += digit
    
    # Check digit is the number that makes total divisible by 10
    check_digit = (10 - (total % 10)) % 10
    return check_digit


def validate_sa_id_simple(id_number: str) -> bool:
    """
    Simple South African ID validation with basic Luhn check
    Less strict on date validation
    """
    if len(id_number) != 13 or not id_number.isdigit():
        return False
    
    # Basic date validation (just check if months/days are plausible)
    try:
        month = int(id_number[2:4])
        day = int(id_number[4:6])
        
        if month < 1 or month > 12:
            return False
        if day < 1 or day > 31:
            return False
            
    except ValueError:
        return False
    
    # Still use Luhn for check digit
    return _validate_luhn_check_digit(id_number)