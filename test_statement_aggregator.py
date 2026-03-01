from pathlib import Path
from statement_aggregator import aggregate_statements_from_directory

if __name__ == "__main__":
    result_tables_dir = Path('golden_test_files/result_tables')
    
    aggregate_statements_from_directory(result_tables_dir)
