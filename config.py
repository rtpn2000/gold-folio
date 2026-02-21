# Loads the environment variables and also storing API keys!

import os
from dotenv import load_dotenv

# Loads the environment automatically.
load_dotenv()

# API Keys.
metalprice_api_key = os.getenv("METALPRICE_KEY")
#goldapi_key = os.getenv("GOLDAPI_KEY")

# Constants.
ounce_to_g = 31.1034768