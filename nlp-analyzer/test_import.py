"""Test script to debug imports"""
import sys
print(f"Python: {sys.version}")
print(f"Path: {sys.executable}")

try:
    print("\n1. Testing pandas import...")
    import pandas as pd
    print("   ✓ pandas imported")
    
    print("\n2. Testing openpyxl import...")
    import openpyxl
    print("   ✓ openpyxl imported")
    
    print("\n3. Testing file read...")
    df = pd.read_excel("TestVeri_Duygulu.xlsx")
    print(f"   ✓ File read successfully: {len(df)} rows")
    print(f"   Columns: {list(df.columns)}")
    
    print("\n4. Testing services import...")
    from services.nlp_service import NLPService
    print("   ✓ NLPService imported")
    
    print("\n5. Testing NLPService initialization...")
    nlp = NLPService()
    print("   ✓ NLPService initialized")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    import traceback
    print(f"\n❌ Error: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
