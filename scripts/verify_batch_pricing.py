
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from services.pricing_config import FEATURE_PRICING, PRICING_MULTIPLIER, BATCH_DISCOUNT

def test_batch_pricing():
    print(f"Current Multiplier: {PRICING_MULTIPLIER}")
    
    # Check phonon
    phonon_price = FEATURE_PRICING['phonon']
    batch_phonon_price = FEATURE_PRICING['batch_phonon']
    discount = BATCH_DISCOUNT['batch_phonon']
    
    expected_batch_phonon = int(phonon_price * (1 - discount))
    
    print(f"Phonon: {phonon_price}")
    print(f"Batch Phonon: {batch_phonon_price} (Expected: {expected_batch_phonon})")
    
    if batch_phonon_price != expected_batch_phonon:
        print("ERROR: Batch phonon price mismatch!")
    else:
        print("Batch phonon price correct.")

    # Check kappa
    kappa_price = FEATURE_PRICING['kappa']
    batch_kappa_price = FEATURE_PRICING['batch_kappa']
    discount_kappa = BATCH_DISCOUNT['batch_kappa']
    
    expected_batch_kappa = int(kappa_price * (1 - discount_kappa))
    
    print(f"Kappa: {kappa_price}")
    print(f"Batch Kappa: {batch_kappa_price} (Expected: {expected_batch_kappa})")
    
    if batch_kappa_price != expected_batch_kappa:
        print("ERROR: Batch kappa price mismatch!")
    else:
        print("Batch kappa price correct.")

if __name__ == "__main__":
    test_batch_pricing()
