import pandas as pd
import requests,io

api_url="https://data.moenv.gov.tw/api/v2/aqx_p_02?api_key=af57253c-e838-46da-a1f5-12b43afd75f3&limit=1000&sort=datacreationdate%20desc&format=CSV"

resp=requests.get(api_url,verify=False)

df=pd.read_csv(io.StringIO(resp.text))

print(df)
