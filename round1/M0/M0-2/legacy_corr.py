import csv

import yaml

CONFIG_PATH = "config.yaml"


def load_config(path=CONFIG_PATH):
    with open(path) as stream:
        return yaml.safe_load(stream)


def load_xy(config):
    csv_path = config["input_csv"]
    col_x = config["columns"]["x"]
    col_y = config["columns"]["y"]

    xs = []
    ys = []
    with open(csv_path) as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            xs.append(float(row[col_x]))
            ys.append(float(row[col_y]))
    return xs, ys


def compute_correlation(xs, ys):
    n = len(xs)

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    dx = 0.0
    dy = 0.0
    prod = 0.0
    for x, y in zip(xs, ys):
        a = x - mean_x
        b = y - mean_y
        dx += a * a
        dy += b * b
        prod += a * b

    denom = dx * dy
    return prod / denom


def main():
    config = load_config()
    xs, ys = load_xy(config)
    r = compute_correlation(xs, ys)

    print("n =", len(xs))
    print("mean_x =", sum(xs) / len(xs))
    print("mean_y =", sum(ys) / len(ys))
    print("r =", r)


if __name__ == "__main__":
    main()