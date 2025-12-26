import pandas as pd


def split_csv_by_row_count(input_file, rows_per_split, output_file_prefix):
    # Load the CSV file
    df = pd.read_csv(input_file)

    # Extract header
    header = df.columns.tolist()

    # Calculate number of splits needed
    total_rows = len(df)
    num_splits = (total_rows // rows_per_split) + (1 if total_rows % rows_per_split != 0 else 0)

    # Split the DataFrame and write to separate CSV files
    for i in range(num_splits):
        start_row = i * rows_per_split
        end_row = start_row + rows_per_split

        # Get the split DataFrame
        df_split = df.iloc[start_row:end_row]

        # Write the split DataFrame to a new CSV file with header
        output_file = f"{output_file_prefix}_part_{i + 1}.csv"
        df_split.to_csv(output_file, index=False, header=True)

    print(f"CSV file '{input_file}' split into {num_splits} files with header in each.")


# Usage
input_file = 'C:/Users/EIMS/Desktop/yokogawa_common/requesters_4_07_Mar_25_07_32.csv'  # Replace with your file name
rows_per_split = 900  # Number of rows per split
output_file_prefix = 'requester'  # Prefix for output files

split_csv_by_row_count(input_file, rows_per_split, output_file_prefix)