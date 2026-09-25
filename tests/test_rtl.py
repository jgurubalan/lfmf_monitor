from lfmf_monitor.rtl import RTLSDR


rtl = RTLSDR()

rtl.start()

samples = rtl.read_samples(1000)

print("Number of samples:", len(samples))
print("Data type:", samples.dtype)
print("First 10 samples:")
print(samples[:10])

rtl.stop()