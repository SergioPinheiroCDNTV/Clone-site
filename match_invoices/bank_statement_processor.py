import os
import pdfplumber
import pandas as pd
from pathlib import Path
import pytesseract
from pdf2image import convert_from_path
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BankStatementProcessor:
    """Processor for bank statements in various formats."""
    
    def __init__(self, input_dir=None):
        """Initialize the bank statement processor.
        
        Args:
            input_dir (str): Directory containing bank statements
        """
        self.input_dir = Path(input_dir) if input_dir else None
        self.supported_extensions = {'.pdf', '.csv', '.xlsx', '.xls'}
        
    def process_statement(self, file_path):
        """Process a bank statement file.
        
        Args:
            file_path (str): Path to the bank statement file
            
        Returns:
            DataFrame: Processed transactions
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        extension = file_path.suffix.lower()
        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file format: {extension}")
            
        if extension == '.pdf':
            return self._process_pdf(file_path)
        elif extension == '.csv':
            return self._process_csv(file_path)
        elif extension in {'.xlsx', '.xls'}:
            return self._process_excel(file_path)
            
    def _process_pdf(self, file_path):
        """Process PDF bank statement using multiple methods."""
        logger.info(f"Processing PDF file: {file_path}")
        
        # Try pdfplumber first (good for searchable PDFs)
        try:
            with pdfplumber.open(file_path) as pdf:
                all_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                        
            if all_text:
                return self._parse_text_content('\n'.join(all_text))
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        # Try OCR if text extraction failed
        try:
            logger.info("Attempting OCR processing...")
            images = convert_from_path(file_path)
            text_content = []
            
            for img in images:
                text = pytesseract.image_to_string(img, lang='por')
                text_content.append(text)
                
            return self._parse_text_content('\n'.join(text_content))
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise
            
    def _parse_text_content(self, text):
        """Parse extracted text into structured data."""
        lines = text.split('\n')
        transactions = []
        
        # Common date patterns
        date_patterns = [
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        
        # Common amount patterns
        amount_patterns = [
            r'-?\d+[\.,]\d{2}',
            r'-?€\s*\d+[\.,]\d{2}',
            r'-?\d{1,3}(?:\.\d{3})*,\d{2}'
        ]
        
        current_date = None
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
                
            # Try to identify transaction lines
            date_match = None
            for pattern in date_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    date_match = match.group()
                    current_date = date_match
                    break
                if date_match:
                    break
            
            # If no date in this line, use the last found date
            if not date_match and current_date:
                date_match = current_date
                
            if not date_match:
                continue
                
            # Extract amount
            amount = None
            for pattern in amount_patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    amount = match.group()
                    # Clean up amount string
                    amount = amount.replace('€', '').replace(' ', '')
                    amount = amount.replace('.', '').replace(',', '.')
                    try:
                        amount = float(amount)
                        break
                    except ValueError:
                        continue
                if amount is not None:
                    break
                    
            if amount is not None:
                # Extract description (everything between date and amount)
                description = line
                for pattern in date_patterns + amount_patterns:
                    description = re.sub(pattern, '', description)
                description = re.sub(r'\s+', ' ', description).strip()
                
                # Check for transaction type indicators
                debit_indicators = ['DB', 'DÉBITO', 'DEBITO', 'PAGAMENTO', 'COMPRA', 'LEVANTAMENTO']
                credit_indicators = ['CR', 'CRÉDITO', 'CREDITO', 'DEPÓSITO', 'DEPOSITO', 'TRANSFERÊNCIA RECEBIDA']
                
                transaction_type = 'UNKNOWN'
                if any(indicator in description.upper() for indicator in debit_indicators):
                    transaction_type = 'DEBIT'
                    if amount > 0:  # Ensure debits are negative
                        amount = -amount
                elif any(indicator in description.upper() for indicator in credit_indicators):
                    transaction_type = 'CREDIT'
                    if amount < 0:  # Ensure credits are positive
                        amount = abs(amount)
                
                transactions.append({
                    'date': date_match,
                    'description': description,
                    'amount': amount,
                    'type': transaction_type
                })
                
        df = pd.DataFrame(transactions)
        if not df.empty:
            # Convert date strings to datetime objects
            df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y', errors='coerce')
            # Sort by date
            df = df.sort_values('date')
            
        return df
        
    def _process_csv(self, file_path):
        """Process CSV bank statement."""
        # Try different encodings
        encodings = ['utf-8', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                return self._standardize_dataframe(df)
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error processing CSV with {encoding} encoding: {e}")
                continue
                
        raise ValueError("Could not process CSV file with any known encoding")
        
    def _process_excel(self, file_path):
        """Process Excel bank statement."""
        try:
            df = pd.read_excel(file_path)
            return self._standardize_dataframe(df)
        except Exception as e:
            logger.error(f"Error processing Excel file: {e}")
            raise
            
    def _standardize_dataframe(self, df):
        """Standardize DataFrame columns and format."""
        # Common column name variations
        date_columns = [col for col in df.columns if any(term in col.lower() for term in ['date', 'data', 'dia'])]
        amount_columns = [col for col in df.columns if any(term in col.lower() for term in ['amount', 'valor', 'montante', 'quantia'])]
        desc_columns = [col for col in df.columns if any(term in col.lower() for term in ['desc', 'texto', 'detalhe'])]
        
        if not all([date_columns, amount_columns, desc_columns]):
            raise ValueError("Could not identify required columns in the file")
            
        # Standardize column names
        df = df.rename(columns={
            date_columns[0]: 'date',
            amount_columns[0]: 'amount',
            desc_columns[0]: 'description'
        })
        
        # Convert date format
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Ensure amount is numeric
        df['amount'] = pd.to_numeric(df['amount'].astype(str).str.replace(',', '.'), errors='coerce')
        
        # Add transaction type based on amount
        df['type'] = df['amount'].apply(lambda x: 'CREDIT' if x > 0 else 'DEBIT')
        
        return df[['date', 'description', 'amount', 'type']].sort_values('date')
        
    def process_directory(self, directory=None):
        """Process all statements in a directory.
        
        Args:
            directory (str, optional): Directory to process. Defaults to input_dir.
            
        Returns:
            DataFrame: Combined transactions from all statements
        """
        directory = Path(directory) if directory else self.input_dir
        if not directory:
            raise ValueError("No directory specified")
            
        all_transactions = []
        
        for file_path in directory.glob('*'):
            if file_path.suffix.lower() in self.supported_extensions:
                try:
                    df = self.process_statement(file_path)
                    if df is not None and not df.empty:
                        df['source_file'] = file_path.name
                        all_transactions.append(df)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    
        if not all_transactions:
            return pd.DataFrame()
            
        result = pd.concat(all_transactions, ignore_index=True)
        result = result.sort_values('date')
        return result