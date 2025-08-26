# Azure AD Graph API Client

A Python module that connects to Microsoft Azure Active Directory (Azure AD) using OAuth 2.0 via the Microsoft Authentication Library (MSAL) and queries Microsoft Graph API for configuration settings.

## 🚀 Features

- **Secure Authentication**: Uses MSAL for OAuth 2.0 client credentials flow
- **Graph API Integration**: Queries Microsoft Graph v1.0 endpoints
- **Configuration Fetching**: Retrieves Conditional Access Policies, Authentication Methods Policy, Password Policies, and Users
- **Error Handling**: Graceful handling of authentication and API errors
- **Reusable Design**: Helper functions for easy extension to other Graph API endpoints

## 📋 Requirements

- Python 3.7+
- Azure AD App Registration with appropriate permissions
- Microsoft Graph API permissions

## 🛠️ Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   - Copy `env_template.txt` to `.env`
   - Fill in your Azure AD credentials:
   ```env
   AZURE_CLIENT_ID=your_client_id_here
   AZURE_TENANT_ID=your_tenant_id_here
   AZURE_CLIENT_SECRET=your_client_secret_here
   ```

## 🔧 Azure AD Setup

### 1. Create App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: Your app name
   - **Supported account types**: Choose based on your needs
   - **Redirect URI**: (Optional for this use case)

### 2. Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Application permissions**
5. Add these permissions:
   - `Policy.Read.All` (for Conditional Access Policies)
   - `Policy.ReadWrite.AuthenticationMethod` (for Authentication Methods Policy)
   - `User.Read.All` (for Users)
   - `Directory.Read.All` (for general directory access)

### 3. Generate Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and choose expiration
4. **Copy the secret value immediately** (you won't see it again)

### 4. Get Required Values

- **Client ID**: Found in the app registration overview
- **Tenant ID**: Found in Azure AD overview
- **Client Secret**: The secret you just created

## 📖 Usage

### Basic Usage

```python
from azure_graph_client import AzureGraphClient

# Initialize the client
client = AzureGraphClient()

# Get all configurations
configurations = client.get_all_configurations()
print(configurations)
```

### Specific Endpoints

```python
# Get Conditional Access Policies
cap_data = client.get_conditional_access_policies()

# Get Authentication Methods Policy
amp_data = client.get_authentication_methods_policy()

# Get Users (first 10)
users_data = client.get_users(top=10)

# Custom endpoint
custom_data = client.fetch_graph_config("/directoryRoles")
```

### Helper Functions

```python
# Get access token
token = client.get_graph_token()

# Fetch any Graph API endpoint
data = client.fetch_graph_config("/your/endpoint")
```

## 🏃‍♂️ Running the Examples

### Main Script
```bash
python azure_graph_client.py
```

### Example Usage
```bash
python example_usage.py
```

## 📊 Available Endpoints

The module includes methods for these Microsoft Graph API endpoints:

- **Conditional Access Policies**: `/conditionalAccess/policies`
- **Authentication Methods Policy**: `/policies/authenticationMethodsPolicy`
- **Password Policies**: `/policies/authenticationFlowsPolicy`
- **Users**: `/users` (with pagination support)

## 🔍 Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Ensure your `.env` file exists and contains all required variables
   - Check that variable names match exactly

2. **"Failed to acquire token"**
   - Verify your client ID, tenant ID, and client secret
   - Check that your app registration has the correct permissions
   - Ensure the client secret hasn't expired

3. **"API request failed with status 403"**
   - Your app registration needs additional permissions
   - Contact your Azure AD administrator

4. **"API request failed with status 401"**
   - Token may have expired
   - Check your credentials and permissions

### Debug Mode

Enable detailed logging by modifying the logging level in `azure_graph_client.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 📁 Project Structure

```
Test Azure/
├── azure_graph_client.py    # Main client module
├── example_usage.py         # Usage examples
├── requirements.txt         # Python dependencies
├── env_template.txt         # Environment variables template
└── README.md               # This file
```

## 🔐 Security Notes

- **Never commit your `.env` file** to version control
- **Rotate client secrets** regularly
- **Use least-privilege permissions** for your app registration
- **Monitor API usage** in Azure AD audit logs

## 📚 References

- [Microsoft Graph API Documentation](https://learn.microsoft.com/en-us/graph/api/resources/azure-ad-overview)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

## 📄 License

This project is provided as-is for educational and development purposes. 