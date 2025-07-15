import base64
import pickle
import sys

# Ensure the 'lib' directory is in the Python path
sys.path.insert(0, '')

# Base64 encoded string
encoded_str = "gAJjbGliLmNvcmUuZGF0YXR5cGUKQXR0cmliRGljdApxACmBcQEoWAkAAABkZWxpbWl0ZXJxAlgGAAAAYXFuaGFkcQNYBQAAAHN0YXJ0cQRYBQAAAHF2YnBxcQVYBAAAAHN0b3BxBlgFAAAAcWt4cHFxB1gCAAAAYXRxCFgDAAAAcXFxcQlYBQAAAHNwYWNlcQpYAwAAAHF6cXELWAYAAABkb2xsYXJxDFgDAAAAcXBxcQ1YBQAAAGhhc2hfcQ5YAwAAAHF1cXEPdX1xEChYCQAAAGF0dHJpYnV0ZXERTlgIAAAAa2V5Y2hlY2txEohYGAAAAF9BdHRyaWJEaWN0X19pbml0aWFsaXNlZHETiHViLg=="

# Decode the base64 string
decoded_bytes = base64.b64decode(encoded_str)

# Unpickle the decoded bytes
unpickled_obj = pickle.loads(decoded_bytes)

# Print the unpickled object
print(unpickled_obj)