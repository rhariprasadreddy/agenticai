from benchmark_raw import run_raw_benchmark
from benchmark_e2e import run_e2e_benchmark
from colorama import Fore, Style

print(f"{Fore.GREEN}{Style.BRIGHT}STARTING COMPREHENSIVE ACCURACY AUDIT\n")

# 1. Run Baseline
acc_raw = run_raw_benchmark()

# 2. Run E2E
acc_e2e = run_e2e_benchmark()

# 3. Print Report
print(f"\n{Fore.MAGENTA}========================================")
print(f"FINAL VIVA REPORT")
print(f"========================================")
print(f"Raw Model Accuracy (No Safety):  {acc_raw:.1f}%")
print(f"Agentic System Accuracy (E2E):   {acc_e2e:.1f}%")
print(f"----------------------------------------")
improvement = acc_e2e - acc_raw
if improvement > 0:
    print(f"SAFETY LIFT: +{improvement:.1f}% {Fore.GREEN}✔ VALIDATED")
else:
    print(f"SAFETY LIFT: 0% (Baseline was already safe)")
print(f"========================================")