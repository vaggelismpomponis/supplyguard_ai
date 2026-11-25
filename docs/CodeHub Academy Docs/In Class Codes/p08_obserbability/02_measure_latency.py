from time import perf_counter, sleep

started = perf_counter()
sleep(0.15)  # Simulate a support-directory lookup.
elapsed_ms = (perf_counter() - started) * 1000
print(f"lookup_team completed in {elapsed_ms:.1f} ms")

