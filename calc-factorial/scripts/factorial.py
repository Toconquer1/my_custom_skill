import sys
import math
import datetime
import os

def main():
    # Check if an argument is provided
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Error: Please provide a number to calculate.")
        sys.exit(1)
        
    try:
        num_str = sys.argv[1]
        num = int(num_str)
        
        if num < 0:
            raise ValueError("Factorial is only defined for non-negative integers.")
            
        result = math.factorial(num)
        
        # Get the directory of the current script to save the log file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(script_dir, "factorial.log")
        
        # Write the execution record to the log file
        # Keeping encoding="utf-8" is a good practice, though purely English text won't trigger errors
        with open(log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] Execution log: Calculated factorial of {num}, result is {result}\n")
            
        # Using basic ASCII output to avoid any terminal decoding issues with Emojis
        print(f"[SUCCESS] {num}! = {result}")
        print(f"[INFO] Log saved to: {log_file}")
        
    except ValueError as e:
        print(f"Error: Invalid input ({e}). Please enter a non-negative integer.")
        sys.exit(1)

if __name__ == "__main__":
    main()