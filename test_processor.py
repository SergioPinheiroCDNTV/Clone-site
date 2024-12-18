from match_invoices.bank_statement_processor import BankStatementProcessor
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)

# Initialize the processor
processor = BankStatementProcessor()

# Process single statement
file_path = "input_invoices/bank_statements/Extratos de Conta 007_2024.pdf"
print(f"\nProcessing file: {file_path}")

try:
    df = processor.process_statement(file_path)
    print("\nProcessed transactions:")
    print(df)
    print(f"\nTotal transactions found: {len(df)}")
    
    if not df.empty:
        print("\nSummary:")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Total credits: {df[df['type'] == 'CREDIT']['amount'].sum():.2f}")
        print(f"Total debits: {df[df['type'] == 'DEBIT']['amount'].sum():.2f}")
        
        # Save to CSV for verification
        output_file = "processed_transactions.csv"
        df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")
except Exception as e:
    print(f"Error processing file: {e}")
