import os
import boto3
import pandas as pd
import json

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["BUCKET_NAME"]
BLS_PREFIX  = os.environ.get("BLS_PREFIX", "bls-data/")
API_PREFIX  = os.environ.get("API_PREFIX", "api-data/")
JSON_FILE_NAME = os.environ.get("JSON_FILE_NAME", "population.json")

def lambda_handler(event, context):
    # Example: fetch one BLS file (adjust key as needed)
    bls_obj = s3.get_object(Bucket=BUCKET_NAME, Key=f"{BLS_PREFIX}pr.data.0.Current")
    part1_df = pd.read_csv(bls_obj["Body"], sep="\t")
    print("Part1 sample:", part1_df.head().to_dict())

    # Fetch the population JSON
    api_obj = s3.get_object(Bucket=BUCKET_NAME, Key=f"{API_PREFIX}{JSON_FILE_NAME}")
    population_json = json.load(api_obj["Body"])
    part2_df = pd.json_normalize(population_json["data"])
    print("Part2 sample:", part2_df.head().to_dict())

    # Simple stats
    df_pop = part2_df.copy()
    df_pop["Year"] = df_pop["Year"].astype(int)
    df_pop_2013_2018 = df_pop[(df_pop["Year"] >= 2013) & (df_pop["Year"] <= 2018)]
    mean_pop = round(df_pop_2013_2018["Population"].mean(), 2)
    std_pop = round(df_pop_2013_2018["Population"].std(), 2)

    print(f"Mean Population (2013–2018): {mean_pop}")
    print(f"Standard Deviation: {std_pop}")

    return {"mean_pop": mean_pop, "std_pop": std_pop}
