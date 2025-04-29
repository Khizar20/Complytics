from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    SUPERADMIN = "SUPERADMIN"
    IT_TEAM = "IT_TEAM"
    COMPLIANCE_TEAM = "COMPLIANCE_TEAM"
    MANAGEMENT_TEAM = "MANAGEMENT_TEAM" 