from typing import Optional
import random
import logging
from django.db import IntegrityError

logger = logging.getLogger(__name__)


def save_unique_code(db_obj, prefix="", retry_on_error=True) -> Optional[str]:
    """Generates a random 6 character code with the pattern letter-number-letter-number-letter-number.
    The code is saved to the db_obj and if it already exists, a new code is generated.
    "0", "O", "1", "I", "L" are excluded because they are hard to differentiate.

    Args:
        db_obj (models.Model instance): The database model instance to update code.

    Returns:
        str: The 6 character code, unique to the sender model or None on error finding unique code.
    """
    ascii_set = "ABCDEFGHJKMNPQRSTUVWXYZ"  # excluding "O", "I", "L"
    digit_set = "23456789"  # excluding "0", "1"
    char_sets = [ascii_set, digit_set] * 3
    code = "".join(random.choice(char) for char in char_sets)

    # Update code in the db_obj, if it raises an already exists error, generate a new code.
    try:
        db_obj.__class__.objects.filter(id=db_obj.id).update(code=code)
    except IntegrityError as e:
        if "unique constraint" in str(e):
            logger.warning(
                f"generate_unique_code: Code {code} already exists for {db_obj.__class__}-{db_obj.id}. Generating a new code."
            )
            return save_unique_code(db_obj)
        else:
            logger.error(
                f"generate_unique_code: {db_obj.__class__}-{db_obj.id} Database IntegrityError:[{e}]"
            )
            if retry_on_error:
                return save_unique_code(db_obj, retry_on_error=False)
            else:
                return None
    except Exception as e:
        logger.error(
            f"generate_unique_code: {db_obj.__class__}-{db_obj.id} Error:[{e}]"
        )
        if retry_on_error:
            return save_unique_code(db_obj, retry_on_error=False)
        else:
            return None
    return f"{prefix}{code}" if prefix else code
