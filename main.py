from agg import aggregate_gold_prices

if __name__ == "__main__":
    data = aggregate_gold_prices()
    print("Aggregated Gold Prices:\n", data)