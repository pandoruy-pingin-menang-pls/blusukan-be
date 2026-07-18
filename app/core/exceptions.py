from fastapi import HTTPException


class OTPExpiredException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"error_code": "OTP_EXPIRED", "message": "Kode OTP sudah kedaluwarsa."})

class OTPRateLimitException(HTTPException):
    def __init__(self):
        super().__init__(status_code=429, detail={"error_code": "OTP_RATE_LIMIT", "message": "Terlalu banyak percobaan OTP. Silakan coba lagi nanti."})

class InvalidLocationException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"error_code": "INVALID_LOCATION", "message": "Lokasi tidak valid."})

class InsufficientBudgetException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"error_code": "INSUFFICIENT_BUDGET", "message": "Saldo atau budget tidak mencukupi."})

class PromoExpiredException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"error_code": "PROMO_EXPIRED", "message": "Promo sudah kedaluwarsa."})

class MerchantOwnershipException(HTTPException):
    def __init__(self):
        super().__init__(status_code=403, detail={"error_code": "FORBIDDEN_NOT_OWNER", "message": "Anda tidak memiliki akses ke merchant ini."})

class DuplicateStampException(HTTPException):
    def __init__(self):
        super().__init__(status_code=409, detail={"error_code": "STAMP_ALREADY_AWARDED", "message": "Stamp sudah diberikan sebelumnya."})

class TokenReuseDetectedException(HTTPException):
    def __init__(self, message="Terdeteksi aktivitas mencurigakan pada sesi Anda. Anda telah dikeluarkan dari semua perangkat demi keamanan."):
        super().__init__(status_code=401, detail={"error_code": "TOKEN_REUSE_DETECTED", "message": message})


class IngestLimitReachedException(HTTPException):
    def __init__(self):
        super().__init__(status_code=429, detail={"error_code": "INGEST_LIMIT_REACHED", "message": "Batas limit tercapai."})

class DuplicateMerchantException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail={"error_code": "MERCHANT_ALREADY_EXISTS", "message": "Anda sudah memiliki profil toko. 1 Akun hanya bisa membuat 1 toko."})

class MerchantNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail={"error_code": "MERCHANT_NOT_FOUND", "message": "Profil toko tidak ditemukan."})
