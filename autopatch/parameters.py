'''
Parameters for the automatic patch-clamp algorithm
'''
# Pressure parameters
param_pressure_near = 25
param_pressure_sealing = -20
param_pressure_ramp_increment = -25 # minimum ramp amplitude
param_pressure_ramp_max = -300.
param_pressure_ramp_duration = 1.15

# Normal resistance range
param_Rmin = 2e6
param_Rmax = 25e6

# Initial distance above the target cell
param_cell_distance = 10

# Increase in resistance indicating obstruction
param_max_R_increase = 1e6

# Maximum length of movement during approach
param_max_distance = 15

# Proportional increase in resistance indicating cell presence
param_cell_R_increase = .15

# Gigaseal resistance
param_gigaseal_R = 1e9

# Minimum time for seal
param_seal_min_time = 15

# Voltage ramp duration and amplitude
param_Vramp_duration = 10.
param_Vramp_amplitude = -.070

# Maximum time for seal formation
param_seal_deadline = 120. #90.

# Maximum cell resistance
param_max_cell_R = 300e6

# Optional zap
param_zap = False
