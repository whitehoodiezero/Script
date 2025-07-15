import os
import sys
import re
import argparse
import base64
import logging
import json
import csv
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import jsbeautifier

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

REGEX_PATTERNS = {
    'google_api': r'AIza[0-9A-Za-z-_]{35}',
    'google_maps_api': r'AIza[0-9A-Za-z-_]{35}',
    'google_client_id': r'AIza[0-9A-Za-z-_]{35}',
    'google_client_secret': r'AIza[0-9A-Za-z-_]{35}',
    'google_service_account': r'AIza[0-9A-Za-z-_]{35}',
    'google_api_key': r'AIza[0-9A-Za-z-_]{35}',
    'google_project_id': r'projects/[a-zA-Z0-9_-]+',
    'google_service_account_key': r'AIza[0-9A-Za-z-_]{35}',
    'google_service_account_email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'google_service_account_private_key': r'-----BEGIN PRIVATE KEY-----',
    'google_service_account_private_key_id': r'[0-9a-fA-F]{32}',
    'google_service_account_private_key_pem': r'-----BEGIN RSA PRIVATE KEY-----',
    'google_service_account_private_key_json': r'{"type": "service_account", "project_id": "[a-zA-Z0-9_-]+", "private_key_id": "[0-9a-fA-F]{32}", "private_key": "-----BEGIN PRIVATE KEY-----[\\s\\S]+?-----END PRIVATE KEY-----"}',
    'google_service_account_private_key_p12': r'-----BEGIN PKCS12-----',
    'api_key': r'AIza[0-9A-Za-z-_]{35}',  
    'firebase': r'AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}',
    'firebase_api_key': r'AIza[0-9A-Za-z-_]{35}',
    'firebase_database_secret': r'AIza[0-9A-Za-z-_]{35}',
    'firebase_auth_domain': r'[a-zA-Z0-9_-]+\.firebaseapp\.com',
    'firebase_storage_bucket': r'[a-zA-Z0-9_-]+\.appspot\.com',
    'firebase_messaging_sender_id': r'[0-9]{12}',
    'firebase_database_url': r'https://[a-zA-Z0-9_-]+\.firebaseio\.com',
    'firebase_project_id': r'[a-zA-Z0-9_-]+',
    'google_captcha': r'6L[0-9A-Za-z-_]{38}|^6[0-9a-zA-Z_-]{39}$',
    'google_recaptcha': r'6L[0-9A-Za-z-_]{38}|^6[0-9a-zA-Z_-]{39}$',
    'google_oauth_client_id': r'AIza[0-9A-Za-z-_]{35}',
    'google_oauth_client_secret': r'AIza[0-9A-Za-z-_]{35}',
    'google_oauth_access_token': r'ya29\.[0-9A-Za-z\-_]+',
    'google_oauth_refresh_token': r'1/[0-9A-Za-z\-_]+',
    'google_oauth_id_token': r'ey[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*$',
    'google_oauth_service_account': r'AIza[0-9A-Za-z-_]{35}',
    'google_oauth_service_account_email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'google_oauth_service_account_private_key': r'-----BEGIN PRIVATE KEY-----',
    'google_oauth_service_account_private_key_id': r'[0-9a-fA-F]{32}',
    'google_oauth_service_account_private_key_pem': r'-----BEGIN RSA PRIVATE KEY-----',
    'google_oauth_service_account_private_key_json': r'{"type": "service_account", "project_id": "[a-zA-Z0-9_-]+", "private_key_id": "[0-9a-fA-F]{32}", "private_key": "-----BEGIN PRIVATE KEY-----[\\s\\S]+?-----END PRIVATE KEY-----"}',
    'google_oauth_service_account_private_key_p12': r'-----BEGIN PKCS12-----',
    'google_oauth': r'ya29\.[0-9A-Za-z\-_]+',
    'amazon_aws_access_key_id': r'A[SK]IA[0-9A-Z]{16}',
    'amazon_aws_secret_access_key': r'AKIA[0-9A-Z]{16}|[A-Za-z0-9/+=]{40}',
    'amazon_aws_session_token': r'FwoGZXIvYXdzEJ3/////////wEaD[0-9a-zA-Z+/=]{40}',
    'amazon_aws_secret_key': r'AKIA[0-9A-Z]{16}|[A-Za-z0-9/+=]{40}',
    'amazon_aws_access_key': r'AKIA[0-9A-Z]{16}',
    'amazon_mws_auth_token': r'amzn\\.mws\\.[0-9a-f-]{36}',
    'facebook_access_token': r'EAACEdEose0cBA[0-9A-Za-z]+',
    'authorization_basic': r'basic [a-zA-Z0-9=:_\+/\-]{5,100}',
    'authorization_bearer': r'bearer [a-zA-Z0-9_\-\.=:_\+/]{5,100}',
    'authorization_api': r'api[key|_key|\s+]+[a-zA-Z0-9_\-]{5,100}',
    'mailgun_api_key': r'key-[0-9a-zA-Z]{32}',
    'twilio_api_key': r'SK[0-9a-fA-F]{32}',
    'twilio_account_sid': r'AC[a-zA-Z0-9_\-]{32}',
    'paypal_braintree_access_token': r'access_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}',
    'stripe_standard_api': r'sk_live_[0-9a-zA-Z]{24}',
    'stripe_test_api': r'sk_test_[0-9a-zA-Z]{24}',
    'stripe_publishable_key': r'pk_live_[0-9a-zA-Z]{24}',
    'stripe_test_publishable_key': r'pk_test_[0-9a-zA-Z]{24}',
    'stripe_secret_key': r'sk_live_[0-9a-zA-Z]{24}',
    'stripe_test_secret_key': r'sk_test_[0-9a-zA-Z]{24}',
    'stripe_connect_api': r'ck_live_[0-9a-zA-Z]{24}',
    'stripe_connect_test_api': r'ck_test_[0-9a-zA-Z]{24}',
    'stripe_connect_restricted_api': r'rk_live_[0-9a-zA-Z]{24}',
    'stripe_connect_restricted_test_api': r'rk_test_[0-9a-zA-Z]{24}',
    'stripe_restricted_api': r'rk_live_[0-9a-zA-Z]{24}',
    'github_access_token': r'[a-zA-Z0-9_-]*:[a-zA-Z0-9_\-]+@github\\.com*',
    'github_personal_access_token': r'ghp_[0-9a-zA-Z]{36}',
    'github_app_id': r'[\d]+',
    'github_oauth_token': r'gho_[0-9a-zA-Z]{36}',
    'github_app_token': r'ghs_[0-9a-zA-Z]{36}',
    'gitlab_access_token': r'glpat-[0-9a-zA-Z]{20,40}',
    'gitlab_oauth_token': r'gl[0-9a-zA-Z]{20,40}',
    'gitlab_personal_access_token': r'glpat-[0-9a-zA-Z]{20,40}',
    'slack_api_token': r'xox[baprs]-[0-9]{10,12}-[0-9a-zA-Z]{24,32}',
    'slack_bot_token': r'xoxb-[0-9]{10,12}-[0-9a-zA-Z]{24,32}',
    'slack_user_token': r'xoxp-[0-9]{10,12}-[0-9a-zA-Z]{24,32}',
    'slack_app_token': r'xoxa-[0-9]{10,12}-[0-9a-zA-Z]{24,32}',
    'slack_oauth_token': r'xox[apbrs]-[0-9]{10,12}-[0-9a-zA-Z]{24,32}',
    'slack_webhook_url': r'https://hooks.slack.com/services/[A-Za-z0-9]{9}/[A-Za-z0-9]{9}/[A-Za-z0-9]{24}',
    'aws_secret_access_key': r'AKIA[0-9A-Z]{16}|[A-Za-z0-9/+=]{40}',
    'aws_session_token': r'FwoGZXIvYXdzEJ3/////////wEaD[0-9a-zA-Z+/=]{40}',
    'aws_access_key_id': r'AKIA[0-9A-Z]{16}',
    'rsa_private_key': r'-----BEGIN RSA PRIVATE KEY-----',
    'ssh_rsa_private_key': r'-----BEGIN RSA PRIVATE KEY-----',
    'ssh_ecdsa_private_key': r'-----BEGIN ECDSA PRIVATE KEY-----',
    'ssh_ed25519_private_key': r'-----BEGIN OPENSSH PRIVATE KEY-----',
    'ssh_rsa_public_key': r'-----BEGIN RSA PUBLIC KEY-----',
    'ssh_ecdsa_public_key': r'-----BEGIN ECDSA PUBLIC KEY-----',
    'ssh_ed25519_public_key': r'-----BEGIN OPENSSH PUBLIC KEY-----',
    'ssh_rsa_cert': r'-----BEGIN SSH RSA CERTIFICATE-----',
    'ssh_ecdsa_cert': r'-----BEGIN SSH ECDSA CERTIFICATE-----',
    'ssh_ed25519_cert': r'-----BEGIN SSH ED25519 CERTIFICATE-----',
    'ssh_dsa_private_key': r'-----BEGIN DSA PRIVATE KEY-----',
    'ssh_dc_private_key': r'-----BEGIN EC PRIVATE KEY-----',
    'pgp_private_block': r'-----BEGIN PGP PRIVATE KEY BLOCK-----',
    'json_web_token': r'ey[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_.+/=]*$',
    'Heroku API KEY': r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',    
    'possible_Creds': r"(?i)(password\s*[`=:\"]+\s*[^\s]+|password is\s*[`=:\"]*\s*[^\s]+|pwd\s*[`=:\"]*\s*[^\s]+|passwd\s*[`=:\"]+\s*[^\s]+)",
    'possible_Creds2': r"(?i)(username\s*[`=:\"]+\s*[^\s]+|user\s*[`=:\"]+\s*[^\s]+|login\s*[`=:\"]+\s*[^\s]+|user is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds3': r"(?i)(api\s*[`=:\"]+\s*[^\s]+|api_key\s*[`=:\"]+\s*[^\s]+|api key\s*[`=:\"],\s*[^\s]+|api_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds4': r"(?i)(token\s*[`=:\"]+\s*[^\s]+|access_token\s*[`=:\"]+\s*[^\s]+|access token\s*[`=:\"]+\s*[^\s]+|token is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds5': r"(?i)(secret\s*[`=:\"]+\s*[^\s]+|secret_key\s*[`=:\"]+\s*[^\s]+|secret key\s*[`=:\"]+\s*[^\s]+|secret is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds6': r"(?i)(auth\s*[`=:\"]+\s*[^\s]+|authentication\s*[`=:\"]+\s*[^\s]+|auth_key\s*[`=:\"]+\s*[^\s]+|auth key\s*[`=:\"]+\s*[^\s]+|auth is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds7': r"(?i)(client_id\s*[`=:\"]+\s*[^\s]+|client_id is\s*[`=:\"]*\s*[^\s]+|client_secret\s*[`=:\"]+\s*[^\s]+|client_secret is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds8': r"(?i)(consumer_key\s*[`=:\"]+\s*[^\s]+|consumer_key is\s*[`=:\"]*\s*[^\s]+|consumer_secret\s*[`=:\"]+\s*[^\s]+|consumer_secret is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds9': r"(?i)(api_secret\s*[`=:\"]+\s*[^\s]+|api_secret is\s*[`=:\"]*\s*[^\s]+|api_secret_key\s*[`=:\"]+\s*[^\s]+|api_secret_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds10': r"(?i)(api_token\s*[`=:\"]+\s*[^\s]+|api_token is\s*[`=:\"]*\s*[^\s]+|api_token_key\s*[`=:\"]+\s*[^\s]+|api_token_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds11': r"(?i)(api_secret_token\s*[`=:\"]+\s*[^\s]+|api_secret_token is\s*[`=:\"]*\s*[^\s]+|api_secret_key_token\s*[`=:\"]+\s*[^\s]+|api_secret_key_token is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds12': r"(?i)(api_access_token\s*[`=:\"]+\s*[^\s]+|api_access_token is\s*[`=:\"]*\s*[^\s]+|api_access_key\s*[`=:\"]+\s*[^\s]+|api_access_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds13': r"(?i)(api_auth_token\s*[`=:\"]+\s*[^\s]+|api_auth_token is\s*[`=:\"]*\s*[^\s]+|api_auth_key\s*[`=:\"]+\s*[^\s]+|api_auth_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds14': r"(?i)(api_client_id\s*[`=:\"]+\s*[^\s]+|api_client_id is\s*[`=:\"]*\s*[^\s]+|api_client_secret\s*[`=:\"]+\s*[^\s]+|api_client_secret is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds15': r"(?i)(api_consumer_key\s*[`=:\"]+\s*[^\s]+|api_consumer_key is\s*[`=:\"]*\s*[^\s]+|api_consumer_secret\s*[`=:\"]+\s*[^\s]+|api_consumer_secret is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds16': r"(?i)(api_key_id\s*[`=:\"]+\s*[^\s]+|api_key_id is\s*[`=:\"]*\s*[^\s]+|api_key_secret\s*[`=:\"]+\s*[^\s]+|api_key_secret is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds17': r"(?i)(api_key_token\s*[`=:\"]+\s*[^\s]+|api_key_token is\s*[`=:\"]*\s*[^\s]+|api_key_token_key\s*[`=:\"]+\s*[^\s]+|api_key_token_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds18': r"(?i)(api_key_access_token\s*[`=:\"]+\s*[^\s]+|api_key_access_token is\s*[`=:\"]*\s*[^\s]+|api_key_access_key\s*[`=:\"]+\s*[^\s]+|api_key_access_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds19': r"(?i)(api_key_auth_token\s*[`=:\"]+\s*[^\s]+|api_key_auth_token is\s*[`=:\"]*\s*[^\s]+|api_key_auth_key\s*[`=:\"]+\s*[^\s]+|api_key_auth_key is\s*[`=:\"]*\s*[^\s]+)",
    'possible_Creds20': r"(?i)(api_key_client_id\s*[`=:\"]+\s*[^\s]+|api_key_client_id is\s*[`=:\"]*\s*[^\s]+|api_key_client_secret\s*[`=:\"]+\s*[^\s]+|api_key_client_secret is\s*[`=:\"]*\s*[^\s]+)",
    'email_address': r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    'ipv4_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
    'port_number': r'\b(?:[0-9]{1,5}|[1-9][0-9]{0,4}|[1-5][0-9]{0,4}|[6-9][0-9]{0,4}|[1-6][0-9]{0,4}|[7-8][0-9]{0,4})\b',
    'mac_address': r'\b(?:[0-9a-fA-F]{2}[:-]){5}(?:[0-9a-fA-F]{2})\b',
    'admin_password': r'(?i)(admin|administrator|root|superuser|sysadmin|webadmin|webmaster|support)\s*[:=]\s*([a-zA-Z0-9!@#$%^&*()_+={}\[\]:;"\'<>,.?/\\|-]{6,})',
    'youtube_api_key': r'AIza[0-9A-Za-z-_]{35}',
    'twitter_api_key': r'(?i)api_key\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'twitter_api_secret_key': r'(?i)api_secret_key\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'twitter_access_token': r'(?i)access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'twitter_access_token_secret': r'(?i)access_token_secret\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'twitter_bearer_token': r'(?i)bearer_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'twitter_oauth_token': r'(?i)oauth_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'twitter_oauth_token_secret': r'(?i)oauth_token_secret\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'twitter_oauth_consumer_key': r'(?i)oauth_consumer_key\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'twitter_oauth_consumer_secret': r'(?i)oauth_consumer_secret\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'twitter_oauth_signature': r'(?i)oauth_signature\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'twitter_oauth_signature_method': r'(?i)oauth_signature_method\s*[:=]\s*([a-zA-Z0-9_-]+)',
    'twitter_oauth_timestamp': r'(?i)oauth_timestamp\s*[:=]\s*([0-9]+)',
    'twitter_oauth_nonce': r'(?i)oauth_nonce\s*[:=]\s*([a-zA-Z0-9_-]+)',
    'twitter_oauth_version': r'(?i)oauth_version\s*[:=]\s*([0-9.]+)',
    'twitter_oauth_callback': r'(?i)oauth_callback\s*[:=]\s*([a-zA-Z0-9_-]+)',
    'twitter_oauth_verifier': r'(?i)oauth_verifier\s*[:=]\s*([a-zA-Z0-9_-]+)',
    'facebook_app_id': r'\b\d{15,20}\b',
    'facebook_app_secret': r'(?i)app_secret\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'facebook_page_access_token': r'(?i)page_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_user_access_token': r'(?i)user_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_long_lived_access_token': r'(?i)long_lived_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_graph_api_token': r'(?i)graph_api_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_graph_api_access_token': r'(?i)graph_api_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_graph_api_app_token': r'(?i)graph_api_app_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_graph_api_page_token': r'(?i)graph_api_page_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_graph_api_user_token': r'(?i)graph_api_user_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_graph_api_long_lived_token': r'(?i)graph_api_long_lived_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'facebook_graph_api_short_lived_token': r'(?i)graph_api_short_lived_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'graphql_api_token': r'(?i)graphql_api_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'graphql_api_access_token': r'(?i)graphql_api_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'graphql_api_app_token': r'(?i)graphql_api_app_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'graphql_api_page_token': r'(?i)graphql_api_page_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'graphql_api_user_token': r'(?i)graphql_api_user_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'graphql_api_long_lived_token': r'(?i)graphql_api_long_lived_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'graphql_api_short_lived_token': r'(?i)graphql_api_short_lived_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'swagger_api_key': r'(?i)swagger_api_key\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'swagger_api_secret_key': r'(?i)swagger_api_secret_key\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'swagger_access_token': r'(?i)swagger_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'swagger_client_id': r'(?i)swagger_client_id\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'swagger_client_secret': r'(?i)swagger_client_secret\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'swagger_oauth_token': r'(?i)swagger_oauth_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'swagger_oauth_client_id': r'(?i)swagger_oauth_client_id\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'swagger_oauth_client_secret': r'(?i)swagger_oauth_client_secret\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'swagger_oauth_access_token': r'(?i)swagger_oauth_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'swagger_oauth_refresh_token': r'(?i)swagger_oauth_refresh_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'swagger_oauth_id_token': r'(?i)swagger_oauth_id_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'swagger_oauth_service_account': r'(?i)swagger_oauth_service_account\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'rest_api_key': r'(?i)rest_api_key\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'rest_api_secret_key': r'(?i)rest_api_secret_key\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'rest_access_token': r'(?i)rest_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'rest_client_id': r'(?i)rest_client_id\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'rest_client_secret': r'(?i)rest_client_secret\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'rest_oauth_token': r'(?i)rest_oauth_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'rest_oauth_client_id': r'(?i)rest_oauth_client_id\s*[:=]\s*([a-zA-Z0-9_-]{32})',
    'rest_oauth_client_secret': r'(?i)rest_oauth_client_secret\s*[:=]\s*([a-zA-Z0-9_-]{64})',
    'rest_oauth_access_token': r'(?i)rest_oauth_access_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'rest_oauth_refresh_token': r'(?i)rest_oauth_refresh_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'rest_oauth_id_token': r'(?i)rest_oauth_id_token\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'rest_oauth_service_account': r'(?i)rest_oauth_service_account\s*[:=]\s*([a-zA-Z0-9_-]{40})',
    'internal_ipv4_address': r'\b(?:10|172\.16|192\.168)\.(?:[0-9]{1,3}\.){2}[0-9]{1,3}\b',
    'external_ipv4_address': r'\b(?:[1-9][0-9]{0,2}|1[0-9]{3}|2[0-4][0-9]{2}|25[0-5])\.(?:[0-9]{1,3}\.){2}(?:[0-9]{1,3})\b',
    'internal_ipv6_address': r'\b(?:[fF][cCdD][0-9a-fA-F]{2}|[fF][eE][8-9a-fA-F]{2}|[fF][eE][0-7][0-9a-fA-F]{2})\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
    'external_ipv6_address': r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
    'local_ipv4_address': r'\b(?:127\.0\.0\.1|localhost)\b',
    'local_ipv6_address': r'\b(?:[fF][cCdD][0-9a-fA-F]{2}|[fF][eE][8-9a-fA-F]{2}|[fF][eE][0-7][0-9a-fA-F]{2})\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
    'ipv6_address': r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b',
    'url': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+',
    'url_inside_code': r"https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+",
    'hex_secret': r"(?i)\b(?:[a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64})\b",
    'base64_secret': r'(?i)(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{4})',
    'base64_url_secret': r'(?i)(?:[A-Za-z0-9_-]{4})*(?:[A-Za-z0-9_-]{2}==|[A-Za-z0-9_-]{3}=|[A-Za-z0-9_-]{4})',
    'Endpoint API Internal': r'(?i)(?:https?://)?(?:[a-zA-Z0-9-]+\.)?[a-zA-Z0-9-]+(?:\.[a-zA-Z]{2,})?(?:/[\w\-._~:/?#\[\]@!$&\'()*+,;=%]*)*',
    'Endpoint API External': r'(?i)(?:https?://)?(?:[a-zA-Z0-9-]+\.)?[a-zA-Z0-9-]+(?:\.[a-zA-Z]{2,})?(?:/[\w\-._~:/?#\[\]@!$&\'()*+,;=%]*)*',
    'Endpoint API Internal v2': r'(dev|stage|staging|test|internal)[.-]?api[.-]?[a-z0-9]+\.(com|local)',
    'Endpoint API External v2': r'(prod|production|live|external)[.-]?api[.-]?[a-z0-9]+\.(com|local)',
    'Generic Secrets in JSON Objects': r'"(?:[a-zA-Z0-9_]+)":\s*"(?:[a-zA-Z0-9_@./-]+)"',
    'Generic Secrets in JSON Objects v2': r"""["'](api[._-]?key|secret|token|password)["']\s*:\s*["'][a-z0-9%/+._~-]{12,64}["']""",
}

class SecretFinder:
    def __init__(self, headers=None, cookies=None, proxies=None, regex_filter=None):
        self.headers = headers or {}
        self.cookies = cookies
        self.proxies = proxies
        self.regex_filter = regex_filter

    def fetch_content(self, url):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        headers = self.headers.copy()
        headers.update({'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
        if self.cookies:
            headers['Cookie'] = self.cookies

        try:
            resp = session.get(url, headers=headers, proxies=self.proxies, timeout=10, verify=False)
            return resp.content.decode(resp.apparent_encoding or 'utf-8', errors='replace')
        except Exception as e:
            err_msg = str(e).encode('ascii', 'replace').decode()
            logging.warning(f"Failed to fetch {url}: {err_msg}")
            return ""

    def extract_secrets(self, content):
        matches = []
        beautified = jsbeautifier.beautify(content) if len(content) < 1_000_000 else content
        for name, pattern in REGEX_PATTERNS.items():
            if self.regex_filter and not re.search(self.regex_filter, name):
                continue
            for match in re.finditer(pattern, beautified, re.I):
                matches.append({
                    'type': name,
                    'match': match.group(0)
                })
        return matches

def parse_args():
    parser = argparse.ArgumentParser(description="Scan JS files or URLs for sensitive data leaks.")
    parser.add_argument("-i", "--input", required=True, nargs='+', help="URLs, local files, or Burp/ZAP XML")
    parser.add_argument("-r", "--regex", help="Filter regex type name")
    parser.add_argument("-c", "--cookie", help="Add cookies if needed")
    parser.add_argument("-H", "--headers", help="Extra headers as 'Key:Value\\nKey2:Value2'")
    parser.add_argument("-p", "--proxy", help="Proxy server (e.g., http://127.0.0.1:8080)")
    parser.add_argument("-o", "--output", help="Output file (.json, .csv, .html, .txt)")
    return parser.parse_args()

def parse_headers(raw):
    headers = {}
    if raw:
        for line in raw.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                headers[key.strip()] = val.strip()
    return headers

def load_burp_zap_xml(path):
    try:
        root = ET.parse(path).getroot()
        items = []
        for item in root.findall('.//item'):
            url = item.find('url').text
            content = base64.b64decode(item.find('response').text).decode('utf-8', 'replace')
            items.append((url, content))
        return items
    except Exception as e:
        logging.error(f"Failed to parse XML {path}: {e}")
        return []

def save_output(path, data):
    if path.endswith(".json"):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif path.endswith(".csv"):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["url", "type", "match"])
            writer.writeheader()
            writer.writerows(data)
    elif path.endswith(".html"):
        with open(path, 'w', encoding='utf-8') as f:
            f.write("<html><body>")
            for row in data:
                f.write(f"<p><b>{row['type']}</b>: {row['match']}<br><small>{row['url']}</small></p>")
            f.write("</body></html>")
    elif path.endswith(".txt"):
        with open(path, 'w', encoding='utf-8') as f:
            for row in data:
                f.write(f"[{row['type']}] {row['match']} (from {row['url']})\n")
    logging.info(f"Saved output to {path}")

def main():
    args = parse_args()
    headers = parse_headers(args.headers)
    proxies = {'http': args.proxy, 'https': args.proxy} if args.proxy else None
    finder = SecretFinder(headers=headers, cookies=args.cookie, proxies=proxies, regex_filter=args.regex)

    input_items = []
    for target in args.input:
        if os.path.isfile(target):
            if target.endswith(".xml"):
                input_items.extend(load_burp_zap_xml(target))
            else:
                with open(target, 'r', encoding='utf-8') as f:
                    for line in f:
                        url = line.strip()
                        if url:
                            input_items.append((url, None))
        else:
            input_items.append((target, None))

    results = []
    def process(pair):
        url, content = pair
        content = content or finder.fetch_content(url)
        leaks = finder.extract_secrets(content)
        if leaks:
            for leak in leaks:
                leak['url'] = url
                results.append(leak)
                try:
                    print(f"[{leak['type']}] {leak['match']} (from {url})")
                except UnicodeEncodeError:
                    print(f"[{leak['type']}] {leak['match'].encode('ascii','replace').decode()} (from {url})")

    with ThreadPoolExecutor(max_workers=5) as exec:
        exec.map(process, input_items)

    if args.output and results:
        save_output(args.output, results)

if __name__ == '__main__':
    main()
