type ECDSACurveParameters = tuple[int, int, int]


ECDSA_CURVE_PARAMETERS: dict[str, ECDSACurveParameters] = {
    "nistp256": (
        0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF,
        0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
        32,
    ),
    "nistp384": (
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFF0000000000000000FFFFFFFF,
        0xB3312FA7E23EE7E4988E056BE3F82D19181D9C6EFE8141120314088F5013875AC656398D8A2ED19D2A85C8EDD3EC2AEF,
        48,
    ),
    "nistp521": (
        (1 << 521) - 1,
        0x0051953EB9618E1C9A1F929A21A0B68540EEA2DA725B99B315F3B8B489918EF109E156193951EC7E937B1652C0BD3BB1BF073573DF883D2C34F1EF451FD46B503F00,
        66,
    ),
}
ED25519_FIELD_PRIME = (1 << 255) - 19
ED25519_CURVE_D = (-121665 * pow(121666, -1, ED25519_FIELD_PRIME)) % ED25519_FIELD_PRIME
ED25519_SQRT_MINUS_ONE = pow(2, (ED25519_FIELD_PRIME - 1) // 4, ED25519_FIELD_PRIME)
ED25519_SUBGROUP_ORDER = (1 << 252) + 27742317777372353535851937790883648493


def validate_rsa_public_numbers(exponent_field: bytes, modulus_field: bytes) -> None:
    exponent = _read_positive_ssh_mpint(value=exponent_field, field_name="RSA exponent")
    modulus = _read_positive_ssh_mpint(value=modulus_field, field_name="RSA modulus")
    if exponent < 3 or exponent % 2 == 0:
        raise ValueError("the RSA exponent must be an odd integer of at least 3")
    if exponent >= modulus:
        raise ValueError("the RSA exponent must be smaller than the modulus")
    if modulus % 2 == 0 or modulus.bit_length() < 1_024:
        raise ValueError("the RSA modulus must be odd and contain at least 1024 bits")


def validate_ecdsa_public_point(curve_name: str, point: bytes) -> None:
    parameters = ECDSA_CURVE_PARAMETERS.get(curve_name)
    if parameters is None:
        raise ValueError(f"unsupported ECDSA curve {curve_name!r}")
    field_prime, curve_b, coordinate_length = parameters
    if len(point) != 1 + 2 * coordinate_length or point[0] != 4:
        raise ValueError("the ECDSA public point is not an uncompressed point of the required size")
    x_coordinate = int.from_bytes(point[1 : 1 + coordinate_length], byteorder="big", signed=False)
    y_coordinate = int.from_bytes(point[1 + coordinate_length :], byteorder="big", signed=False)
    if x_coordinate >= field_prime or y_coordinate >= field_prime:
        raise ValueError("the ECDSA public point coordinates are outside the curve field")
    expected_y_squared = (pow(x_coordinate, 3, field_prime) - 3 * x_coordinate + curve_b) % field_prime
    if pow(y_coordinate, 2, field_prime) != expected_y_squared:
        raise ValueError("the ECDSA public point is not on the declared curve")


def validate_ed25519_public_key(public_key: bytes) -> None:
    if len(public_key) != 32:
        raise ValueError("an Ed25519 key must contain 32 public-key bytes")
    encoded_y = int.from_bytes(public_key, byteorder="little", signed=False)
    x_sign = encoded_y >> 255
    y_coordinate = encoded_y & ((1 << 255) - 1)
    if y_coordinate >= ED25519_FIELD_PRIME:
        raise ValueError("the Ed25519 public-key encoding is non-canonical")

    y_squared = pow(y_coordinate, 2, ED25519_FIELD_PRIME)
    denominator = (ED25519_CURVE_D * y_squared + 1) % ED25519_FIELD_PRIME
    if denominator == 0:
        raise ValueError("the Ed25519 public-key encoding is not a curve point")
    x_squared = ((y_squared - 1) * pow(denominator, -1, ED25519_FIELD_PRIME)) % ED25519_FIELD_PRIME
    x_coordinate = pow(x_squared, (ED25519_FIELD_PRIME + 3) // 8, ED25519_FIELD_PRIME)
    if pow(x_coordinate, 2, ED25519_FIELD_PRIME) != x_squared:
        x_coordinate = (x_coordinate * ED25519_SQRT_MINUS_ONE) % ED25519_FIELD_PRIME
    if pow(x_coordinate, 2, ED25519_FIELD_PRIME) != x_squared:
        raise ValueError("the Ed25519 public-key encoding is not a curve point")
    if x_coordinate == 0 and x_sign == 1:
        raise ValueError("the Ed25519 public-key x-coordinate has a non-canonical sign")
    if x_coordinate % 2 != x_sign:
        x_coordinate = ED25519_FIELD_PRIME - x_coordinate
    if _ed25519_scalar_multiply(
        point=(x_coordinate, y_coordinate), scalar=ED25519_SUBGROUP_ORDER
    ) != (0, 1):
        raise ValueError("the Ed25519 public key is not in the prime-order subgroup")
    if (x_coordinate, y_coordinate) == (0, 1):
        raise ValueError("the Ed25519 identity point is not a valid public key")


def _read_positive_ssh_mpint(value: bytes, field_name: str) -> int:
    if value == b"":
        raise ValueError(f"the {field_name} is empty")
    if value[0] & 0x80:
        raise ValueError(f"the {field_name} is negative")
    if len(value) > 1 and value[0] == 0 and not value[1] & 0x80:
        raise ValueError(f"the {field_name} uses a non-canonical leading zero")
    number = int.from_bytes(value, byteorder="big", signed=False)
    if number == 0:
        raise ValueError(f"the {field_name} must be positive")
    return number


def _ed25519_scalar_multiply(point: tuple[int, int], scalar: int) -> tuple[int, int]:
    result = (0, 1)
    addend = point
    remaining_scalar = scalar
    while remaining_scalar > 0:
        if remaining_scalar & 1:
            result = _ed25519_add(left=result, right=addend)
        addend = _ed25519_add(left=addend, right=addend)
        remaining_scalar >>= 1
    return result


def _ed25519_add(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
    left_x, left_y = left
    right_x, right_y = right
    product = ED25519_CURVE_D * left_x * right_x * left_y * right_y % ED25519_FIELD_PRIME
    x_numerator = (left_x * right_y + left_y * right_x) % ED25519_FIELD_PRIME
    y_numerator = (left_y * right_y + left_x * right_x) % ED25519_FIELD_PRIME
    x_coordinate = x_numerator * pow(1 + product, -1, ED25519_FIELD_PRIME) % ED25519_FIELD_PRIME
    y_coordinate = y_numerator * pow(1 - product, -1, ED25519_FIELD_PRIME) % ED25519_FIELD_PRIME
    return x_coordinate, y_coordinate
