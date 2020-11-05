# coding=utf-8
# this python routine load the ElveflowDLL.
# It defines all function prototype for use with python lib

from ctypes import *
ElveflowDLL=CDLL('C:/Users/inters/Elveflow SDK V3_01_04/DLL64/DLL64/Elveflow64.dll')# change this path


 # Elveflow Library
 # AF1 Device
 #
 # IInitiate the AF1 device using device name (could be obtained in NI MAX),
 # and regulator, and sensor. It return the AF1 ID (number >=0) to be used
 # with other function
 #
def AF1_Initialization (Device_Name, Pressure_Regulator, Sensor, AF1_ID_out):
	X_AF1_Initialization=ElveflowDLL.AF1_Initialization
	X_AF1_Initialization.argtypes=[c_char_p, c_uint16, c_uint16, POINTER(c_int32)]
	return X_AF1_Initialization (Device_Name, Pressure_Regulator, Sensor, AF1_ID_out)



 # Elveflow Library
 # Sensor Reader or Flow Reader Device
 #
 # Initiate the F_S_R device using device name (could be obtained in NI MAX)
 # and sensors. It return the F_S_R ID (number >=0) to be used with other
 # function.
 # NB: Flow reader can only accept Flow sensor
 # NB 2: Sensor connected to channel 1-2 and 3-4 should be the same type
 # otherwise they will not be taken into account and the user will be informed
 # by a prompt message.
 #
def F_S_R_Initialization (Device_Name, Sens_Ch_1, Sens_Ch_2, Sens_Ch_3, Sens_Ch_4, F_S_Reader_ID_out):
	X_F_S_R_Initialization=ElveflowDLL.F_S_R_Initialization
	X_F_S_R_Initialization.argtypes=[c_char_p, c_uint16, c_uint16, c_uint16, c_uint16, POINTER(c_int32)]
	return X_F_S_R_Initialization (Device_Name, Sens_Ch_1, Sens_Ch_2, Sens_Ch_3, Sens_Ch_4, F_S_Reader_ID_out)



 # Elveflow Library
 # Mux Device
 #
 # Initiate the MUX device using device name (could be obtained in NI MAX). It
 # return the F_S_R ID (number >=0) to be used with other function
 #
def MUX_Initialization (Device_Name, MUX_ID_out):
	X_MUX_Initialization=ElveflowDLL.MUX_Initialization
	X_MUX_Initialization.argtypes=[c_char_p, POINTER(c_int32)]
	return X_MUX_Initialization (Device_Name, MUX_ID_out)



 # Elveflow Library
 # Mux Device
 #
 # Valves are set by a array of 16 element. If the valve value is equal or
 # below 0, valve is close, if it's equal or above 1 the valve is open. The
 # index in the array indicate the selected  valve as shown below :
 # 0   1   2   3
 # 4   5   6   7
 # 8   9   10  11
 # 12  13  14  15
 # If the array does not contain exactly 16 element nothing happened
 #
 #
# use ctypes c_int32*16 for array_valve_in
def MUX_Set_all_valves (MUX_ID_in, array_valve_in, len):
	X_MUX_Set_all_valves=ElveflowDLL.MUX_Set_all_valves
	X_MUX_Set_all_valves.argtypes=[c_int32, POINTER(c_int32), c_int32]
	return X_MUX_Set_all_valves (MUX_ID_in, array_valve_in, len)



 # Elveflow Library
 # MUXDistributor Device
 #
 # Initiate the MUX Distributor device using device com port (ASRLXXX::INSTR
 # where XXX is the com port that could be found in windows device manager).
 # It return the MUX Distributor ID (number >=0) to be used with other
 # function
 #
def MUX_Dist_Initialization (Visa_COM, MUX_Dist_ID_out):
	X_MUX_Dist_Initialization=ElveflowDLL.MUX_Dist_Initialization
	X_MUX_Dist_Initialization.argtypes=[c_char_p, POINTER(c_int32)]
	return X_MUX_Dist_Initialization (Visa_COM, MUX_Dist_ID_out)



 # Elveflow Library
 # OB1 Device
 #
 # Initialize the OB1 device using device name and regulators type (see SDK
 # Z_regulator_type for corresponding numbers). It modify the OB1 ID (number
 # >=0). This ID can be used be used with other function to identify the
 # targed OB1. If an error occurs during the initialization process, the OB1
 # ID value will be -1.
 #
def OB1_Initialization (Device_Name, Reg_Ch_1, Reg_Ch_2, Reg_Ch_3, Reg_Ch_4, OB1_ID_out):
	X_OB1_Initialization=ElveflowDLL.OB1_Initialization
	X_OB1_Initialization.argtypes=[c_char_p, c_uint16, c_uint16, c_uint16, c_uint16, POINTER(c_int32)]
	return X_OB1_Initialization (Device_Name, Reg_Ch_1, Reg_Ch_2, Reg_Ch_3, Reg_Ch_4, OB1_ID_out)



 # Elveflow Library
 # OB1-AF1 Device
 #
 # Set default Calib in Calib cluster, len is the Calib_Array_out array length
 #
# use ctypes c_double*1000 for calibration array
def Elveflow_Calibration_Default (Calib_Array_out, len):
	X_Elveflow_Calibration_Default=ElveflowDLL.Elveflow_Calibration_Default
	X_Elveflow_Calibration_Default.argtypes=[POINTER(c_double*1000), c_int32]
	return X_Elveflow_Calibration_Default (Calib_Array_out, len)



 # Elveflow Library
 # OB1-AF1 Device
 #
 # Load the calibration file located at Path and returns the calibration
 # parameters in the Calib_Array_out. len is the Calib_Array_out array length.
 # The function asks the user to choose the path if Path is not valid, empty
 # or not a path. The function indicate if the file was found.
 #
# use ctypes c_double*1000 for calibration array
def Elveflow_Calibration_Load (Path, Calib_Array_out, len):
	X_Elveflow_Calibration_Load=ElveflowDLL.Elveflow_Calibration_Load
	X_Elveflow_Calibration_Load.argtypes=[c_char_p, POINTER(c_double*1000), c_int32]
	return X_Elveflow_Calibration_Load (Path, Calib_Array_out, len)



 # Elveflow Library
 # OB1-AF1 Device
 #
 # Save the Calibration cluster in the file located at Path. len is the
 # Calib_Array_in array length. The function prompt the user to choose the
 # path if Path is not valid, empty or not a path.
 #
# use ctypes c_double*1000 for calibration array
def Elveflow_Calibration_Save (Path, Calib_Array_in, len):
	X_Elveflow_Calibration_Save=ElveflowDLL.Elveflow_Calibration_Save
	X_Elveflow_Calibration_Save.argtypes=[c_char_p, POINTER(c_double*1000), c_int32]
	return X_Elveflow_Calibration_Save (Path, Calib_Array_in, len)



 # Elveflow Library
 # OB1 Device
 #
 # Launch OB1 calibration and return the calibration array. Before
 # Calibration, ensure that ALL channels are proprely closed with adequate
 # caps.
 # Len correspond to the Calib_array_out length.
 #
# use ctypes c_double*1000 for calibration array
def OB1_Calib (OB1_ID_in, Calib_array_out, len):
	X_OB1_Calib=ElveflowDLL.OB1_Calib
	X_OB1_Calib.argtypes=[c_int32, POINTER(c_double*1000), c_int32]
	return X_OB1_Calib (OB1_ID_in, Calib_array_out, len)



 # Elveflow Library
 # OB1 Device
 #
 #
 # Get the pressure of an OB1 channel.
 #
 # Calibration array is required (use Set_Default_Calib if required) and
 # return a double . Len correspond to the Calib_array_in length.
 #
 # If Acquire_data is true, the OB1 acquires ALL regulator AND ALL analog
 # sensor value. They are stored in the computer memory. Therefore, if several
 # regulator values (OB1_Get_Press) and/or sensor values (OB1_Get_Sens_Data)
 # have to be acquired simultaneously, set the Acquire_Data to true only for
 # the First function. All the other can used the values stored in memory and
 # are almost instantaneous.
 #
# use ctypes c_double*1000 for calibration array
# use ctype c_double*4 for pressure array
def OB1_Get_Press (OB1_ID, Channel_1_to_4, Acquire_Data1True0False, Calib_array_in, Pressure, len):
	X_OB1_Get_Press=ElveflowDLL.OB1_Get_Press
	X_OB1_Get_Press.argtypes=[c_int32, c_int32, c_int32, POINTER(c_double*1000), POINTER(c_double), c_int32]
	return X_OB1_Get_Press (OB1_ID, Channel_1_to_4, Acquire_Data1True0False, Calib_array_in, Pressure, len)



 # Elveflow Library
 # OB1 Device
 #
 # Set the pressure of the OB1 selected channel, Calibration array is required
 # (use Set_Default_Calib if required). Len correspond to the Calib_array_in
 # length.
 #
# use ctypes c_double*1000 for calibration array
def OB1_Set_Press (OB1_ID, Channel_1_to_4, Pressure, Calib_array_in, len):
	X_OB1_Set_Press=ElveflowDLL.OB1_Set_Press
	X_OB1_Set_Press.argtypes=[c_int32, c_int32, c_double, POINTER(c_double*1000), c_int32]
	return X_OB1_Set_Press (OB1_ID, Channel_1_to_4, Pressure, Calib_array_in, len)



 # Elveflow Library
 # AF1 Device
 #
 # Launch AF1 calibration and return the calibration array. Len correspond to
 # the Calib_array_out length.
 #
# use ctypes c_double*1000 for calibration array
def AF1_Calib (AF1_ID_in, Calib_array_out, len):
	X_AF1_Calib=ElveflowDLL.AF1_Calib
	X_AF1_Calib.argtypes=[c_int32, POINTER(c_double*1000), c_int32]
	return X_AF1_Calib (AF1_ID_in, Calib_array_out, len)



 # Elveflow Library
 # AF1 Device
 #
 # Get the pressure of the AF1 device, Calibration array is required (use
 # Set_Default_Calib if required). Len correspond to the Calib_array_in
 # length.
 #
# use ctypes c_double*1000 for calibration array
def AF1_Get_Press (AF1_ID_in, Integration_time, Calib_array_in, Pressure, len):
	X_AF1_Get_Press=ElveflowDLL.AF1_Get_Press
	X_AF1_Get_Press.argtypes=[c_int32, c_int32, POINTER(c_double*1000), POINTER(c_double), c_int32]
	return X_AF1_Get_Press (AF1_ID_in, Integration_time, Calib_array_in, Pressure, len)



 # Elveflow Library
 # AF1 Device
 #
 # Set the pressure of the AF1 device, Calibration array is required (use
 # Set_Default_Calib if required).Len correspond to the Calib_array_in length.
 #
 #
# use ctypes c_double*1000 for calibration array
def AF1_Set_Press (AF1_ID_in, Pressure, Calib_array_in, len):
	X_AF1_Set_Press=ElveflowDLL.AF1_Set_Press
	X_AF1_Set_Press.argtypes=[c_int32, c_double, POINTER(c_double*1000), c_int32]
	return X_AF1_Set_Press (AF1_ID_in, Pressure, Calib_array_in, len)



 # Elveflow Library
 # OB1 Device
 #
 # Close communication with OB1
 #
def OB1_Destructor (OB1_ID):
	X_OB1_Destructor=ElveflowDLL.OB1_Destructor
	X_OB1_Destructor.argtypes=[c_int32]
	return X_OB1_Destructor (OB1_ID)



 # Elveflow Library
 # OB1 Device
 #
 # Read the sensor of the requested channel. ! This Function only convert data
 # that are acquired in OB1_Acquire_data
 # Units : Flow sensor �l/min
 # Pressure : mbar
 #
 # If Acquire_data is true, the OB1 acquires ALL regulator AND ALL analog
 # sensor value. They are stored in the computer memory. Therefore, if several
 # regulator values (OB1_Get_Press) and/or sensor values (OB1_Get_Sens_Data)
 # have to be acquired simultaneously, set the Acquire_Data to true only for
 # the First function. All the other can used the values stored in memory and
 # are almost instantaneous. For Digital Sensor, that required another
 # communication protocol, this parameter have no impact
 #
 # NB: For Digital Flow Senor, If the connection is lots, OB1 will be reseted
 # and the return value will be zero
 #
def OB1_Get_Sens_Data (OB1_ID, Channel_1_to_4, Acquire_Data1True0False, Sens_Data):
	X_OB1_Get_Sens_Data=ElveflowDLL.OB1_Get_Sens_Data
	X_OB1_Get_Sens_Data.argtypes=[c_int32, c_int32, c_int32, POINTER(c_double)]
	return X_OB1_Get_Sens_Data (OB1_ID, Channel_1_to_4, Acquire_Data1True0False, Sens_Data)



 # Elveflow Library
 # OB1 Device
 #
 # Get the trigger of the OB1 (0 = 0V, 1 =3,3V)
 #
def OB1_Get_Trig (OB1_ID, Trigger):
	X_OB1_Get_Trig=ElveflowDLL.OB1_Get_Trig
	X_OB1_Get_Trig.argtypes=[c_int32, POINTER(c_int32)]
	return X_OB1_Get_Trig (OB1_ID, Trigger)



 # Elveflow Library
 # OB1 Device
 #
 # Set the trigger of the OB1 (0 = 0V, 1 =3,3V)
 #
def OB1_Set_Trig (OB1_ID, trigger):
	X_OB1_Set_Trig=ElveflowDLL.OB1_Set_Trig
	X_OB1_Set_Trig.argtypes=[c_int32, c_int32]
	return X_OB1_Set_Trig (OB1_ID, trigger)



 # Elveflow Library
 # AF1 Device
 #
 # Close Communication with AF1
 #
def AF1_Destructor (AF1_ID_in):
	X_AF1_Destructor=ElveflowDLL.AF1_Destructor
	X_AF1_Destructor.argtypes=[c_int32]
	return X_AF1_Destructor (AF1_ID_in)



 # Elveflow Library
 # AF1 Device
 #
 # Get the Flow rate from the flow sensor connected on the AF1
 #
def AF1_Get_Flow_rate (AF1_ID_in, Flow):
	X_AF1_Get_Flow_rate=ElveflowDLL.AF1_Get_Flow_rate
	X_AF1_Get_Flow_rate.argtypes=[c_int32, POINTER(c_double)]
	return X_AF1_Get_Flow_rate (AF1_ID_in, Flow)



 # Elveflow Library
 # AF1 Device
 #
 # Get the trigger of the AF1 device (0=0V, 1=5V).
 #
 #
def AF1_Get_Trig (AF1_ID_in, trigger):
	X_AF1_Get_Trig=ElveflowDLL.AF1_Get_Trig
	X_AF1_Get_Trig.argtypes=[c_int32, POINTER(c_int32)]
	return X_AF1_Get_Trig (AF1_ID_in, trigger)



 # Elveflow Library
 # AF1 Device
 #
 # Set the Trigger of the AF1 device (0=0V, 1=5V).
 #
def AF1_Set_Trig (AF1_ID_in, trigger):
	X_AF1_Set_Trig=ElveflowDLL.AF1_Set_Trig
	X_AF1_Set_Trig.argtypes=[c_int32, c_int32]
	return X_AF1_Set_Trig (AF1_ID_in, trigger)



 # Elveflow Library
 # Sensor Reader or Flow Reader Device
 #
 # Close Communication with F_S_R.
 #
def F_S_R_Destructor (F_S_Reader_ID_in):
	X_F_S_R_Destructor=ElveflowDLL.F_S_R_Destructor
	X_F_S_R_Destructor.argtypes=[c_int32]
	return X_F_S_R_Destructor (F_S_Reader_ID_in)



 # Elveflow Library
 # Sensor Reader or Flow Reader Device
 #
 # Get the data from the selected channel.
 #
def F_S_R_Get_Sensor_data (F_S_Reader_ID_in, Channel_1_to_4, output):
	X_F_S_R_Get_Sensor_data=ElveflowDLL.F_S_R_Get_Sensor_data
	X_F_S_R_Get_Sensor_data.argtypes=[c_int32, c_int32, POINTER(c_double)]
	return X_F_S_R_Get_Sensor_data (F_S_Reader_ID_in, Channel_1_to_4, output)



 # Elveflow Library
 # Mux Device
 #
 # Close the communication of the MUX device
 #
def MUX_Destructor (MUX_ID_in):
	X_MUX_Destructor=ElveflowDLL.MUX_Destructor
	X_MUX_Destructor.argtypes=[c_int32]
	return X_MUX_Destructor (MUX_ID_in)



 # Elveflow Library
 # Mux Device
 #
 # Get the trigger of the MUX device (0=0V, 1=5V).
 #
def MUX_Get_Trig (MUX_ID_in, Trigger):
	X_MUX_Get_Trig=ElveflowDLL.MUX_Get_Trig
	X_MUX_Get_Trig.argtypes=[c_int32, POINTER(c_int32)]
	return X_MUX_Get_Trig (MUX_ID_in, Trigger)



 # Elveflow Library
 # Mux Device
 #
 # Set the state of one valve of the instrument. The desired valve is
 # addressed using Input and Output parameter which corresponds to the
 # fluidics inputs and outputs of the instrument.
 #
def MUX_Set_indiv_valve (MUX_ID_in, Input, Ouput, OpenClose):
	X_MUX_Set_indiv_valve=ElveflowDLL.MUX_Set_indiv_valve
	X_MUX_Set_indiv_valve.argtypes=[c_int32, c_int32, c_int32, c_int32]
	return X_MUX_Set_indiv_valve (MUX_ID_in, Input, Ouput, OpenClose)



 # Elveflow Library
 # Mux Device
 #
 # Set the Trigger of the MUX device (0=0V, 1=5V).
 #
def MUX_Set_Trig (MUX_ID_in, Trigger):
	X_MUX_Set_Trig=ElveflowDLL.MUX_Set_Trig
	X_MUX_Set_Trig.argtypes=[c_int32, c_int32]
	return X_MUX_Set_Trig (MUX_ID_in, Trigger)



 # Elveflow Library
 # MUXDistributor Device
 #
 # Close Communication with MUX distributor device
 #
def MUX_Dist_Destructor (MUX_Dist_ID_in):
	X_MUX_Dist_Destructor=ElveflowDLL.MUX_Dist_Destructor
	X_MUX_Dist_Destructor.argtypes=[c_int32]
	return X_MUX_Dist_Destructor (MUX_Dist_ID_in)



 # Elveflow Library
 # MUXDistributor Device
 #
 # Get the active valve
 #
def MUX_Dist_Get_Valve (MUX_Dist_ID_in, selected_Valve):
	X_MUX_Dist_Get_Valve=ElveflowDLL.MUX_Dist_Get_Valve
	X_MUX_Dist_Get_Valve.argtypes=[c_int32, POINTER(c_int32)]
	return X_MUX_Dist_Get_Valve (MUX_Dist_ID_in, selected_Valve)



 # Elveflow Library
 # MUXDistributor Device
 #
 # Set the active valve
 #
def MUX_Dist_Set_Valve (MUX_Dist_ID_in, selected_Valve):
	X_MUX_Dist_Set_Valve=ElveflowDLL.MUX_Dist_Set_Valve
	X_MUX_Dist_Set_Valve.argtypes=[c_int32, c_int32]
	return X_MUX_Dist_Set_Valve (MUX_Dist_ID_in, selected_Valve)



 # Elveflow Library
 # OB1 Device
 #
 # Add sensor to OB1 device. Selecte the channel n� (1-4) the sensor type.
 #
 # For Flow sensor, the type of communication (Analog/Digital) and the
 # Calibration for digital version (H20 or IPA) should be specify. (see SDK
 # user guide,  Z_sensor_type_type , Z_sensor_digit_analog, and
 # Z_Sensor_FSD_Calib for number correspnodance)
 #
 # For digital version, the sensor type is automatically detected during this
 # function call.
 #
 # For Analog sensor, the calibration parameters is not taken into account.
 #
 # If the sensor is not compatible with the OB1 version, or no digital sensor
 # are detected a an error will be thrown as output of the function.
 #
def OB1_Add_Sens (OB1_ID, Channel_1_to_4, SensorType, DigitalAnalog, FSens_Digit_Calib):
	X_OB1_Add_Sens=ElveflowDLL.OB1_Add_Sens
	X_OB1_Add_Sens.argtypes=[c_int32, c_int32, c_uint16, c_uint16, c_uint16]
	return X_OB1_Add_Sens (OB1_ID, Channel_1_to_4, SensorType, DigitalAnalog, FSens_Digit_Calib)



 # Elveflow Library
 # BFS Device
 #
 # Close Communication with BFS device
 #
def BFS_Destructor (BFS_ID_in):
	X_BFS_Destructor=ElveflowDLL.BFS_Destructor
	X_BFS_Destructor.argtypes=[c_int32]
	return X_BFS_Destructor (BFS_ID_in)



 # Elveflow Library
 # BFS Device
 #
 # Initiate the BFS device using device com port (ASRLXXX::INSTR where XXX is
 # the com port that could be found in windows device manager). It return the
 # BFS ID (number >=0) to be used with other function
 #
def BFS_Initialization (Visa_COM, BFS_ID_out):
	X_BFS_Initialization=ElveflowDLL.BFS_Initialization
	X_BFS_Initialization.argtypes=[c_char_p, POINTER(c_int32)]
	return X_BFS_Initialization (Visa_COM, BFS_ID_out)



 # Elveflow Library
 # BFS Device
 #
 # Get fluid density (in g/L) for the BFS defined by the BFS_ID
 #
def BFS_Get_Density (BFS_ID_in, Density):
	X_BFS_Get_Density=ElveflowDLL.BFS_Get_Density
	X_BFS_Get_Density.argtypes=[c_int32, POINTER(c_double)]
	return X_BFS_Get_Density (BFS_ID_in, Density)



 # Elveflow Library
 # BFS Device
 #
 # Get Frow rate (in �l/min) of the BFS defined by the BFS_ID
 #
def BFS_Get_Flow (BFS_ID_in, Flow):
	X_BFS_Get_Flow=ElveflowDLL.BFS_Get_Flow
	X_BFS_Get_Flow.argtypes=[c_int32, POINTER(c_double)]
	return X_BFS_Get_Flow (BFS_ID_in, Flow)



 # Elveflow Library
 # BFS Device
 #
 # Get the fluid temperature (in �C) of the BFS defined by the BFS_ID
 #
def BFS_Get_Temperature (BFS_ID_in, Temperature):
	X_BFS_Get_Temperature=ElveflowDLL.BFS_Get_Temperature
	X_BFS_Get_Temperature.argtypes=[c_int32, POINTER(c_double)]
	return X_BFS_Get_Temperature (BFS_ID_in, Temperature)



 # Elveflow Library
 # BFS Device
 #
 # Elveflow Library
 # BFS Device
 #
 # Set the instruement Filter. 0.000001= maximum filter -> slow change but
 # very low noise.  1= no filter-> fast change but noisy.
 #
 # Default value is 0.1
 #
def BFS_Set_Filter (BFS_ID_in, Filter_value):
	X_BFS_Set_Filter=ElveflowDLL.BFS_Set_Filter
	X_BFS_Set_Filter.argtypes=[c_int32, c_double]
	return X_BFS_Set_Filter (BFS_ID_in, Filter_value)



 # Elveflow Library - ONLY FOR ILLUSTRATION -
 # OB1 and AF1 Devices
 #
 # This function is only provided for illustration purpose, to explain how to
 # do your own feedback loop. Elveflow do not warranty neither efficient nor
 # optimum regulation with this illustration of PI regulator . With this
 # function the PI parameters have to be tuned for every regulator and every
 # microfluidic circuit.
 #
 # In this function need to be initiate with a first call where PID_ID =-1.
 # The PID_out will provide the new created PID_ID. This ID should be use in
 # further call.
 #
 # General remarks of this PI regulator :
 #
 # The error "e" is calculate for every step as e=target value-actual value
 # There are 2 contributions to a PI regulator: proportionl contribution which
 # only depend on this step and  Prop=e#P and integral part which is the
 # "memory" of the regulator. This value is calculated as
 # Integ=integral(I#e#dt) and can be reset.
 #
 #
def Elveflow_EXAMPLE_PID (PID_ID_in, actualValue, Reset, P, I, PID_ID_out, value):
	X_Elveflow_EXAMPLE_PID=ElveflowDLL.Elveflow_EXAMPLE_PID
	X_Elveflow_EXAMPLE_PID.argtypes=[c_int32, c_double, c_int32, c_double, c_double, POINTER(c_int32), POINTER(c_double)]
	return X_Elveflow_EXAMPLE_PID (PID_ID_in, actualValue, Reset, P, I, PID_ID_out, value)



 # Elveflow Library
 # Mux Device
 #
 # Valves are set by a array of 16 element. If the valve value is equal or
 # below 0, valve is close, if it's equal or above 1 the valve is open. If the
 # array does not contain exactly 16 element nothing happened
 #
 #
def MUX_Wire_Set_all_valves (MUX_ID_in, array_valve_in, len):
	X_MUX_Wire_Set_all_valves=ElveflowDLL.MUX_Wire_Set_all_valves
	X_MUX_Wire_Set_all_valves.argtypes=[c_int32, POINTER(c_int32), c_int32]
	return X_MUX_Wire_Set_all_valves (MUX_ID_in, array_valve_in, len)



 # Elveflow Library
 # OB1 Device
 #
 # Set the pressure of all the channel of the selected OB1. Calibration array
 # is required (use Set_Default_Calib if required). Len correspond to the
 # Calib_array_in length. It uses an array as pressures input. Len2
 # corresponds to the the pressure input array. The first number of the array
 # correspond to the first channel, the seconds number to the seconds channels
 # and so on. All the number above 4 are not taken into account.
 #
 # If only One channel need to be set, use OB1_Set_Pressure.
 #
def OB1_Set_All_Press (OB1_ID, Pressure_array_in, Calib_array_in, len, len2):
	X_OB1_Set_All_Press=ElveflowDLL.OB1_Set_All_Press
	X_OB1_Set_All_Press.argtypes=[c_int32, POINTER(c_double), POINTER(c_double), c_int32, c_int32]
	return X_OB1_Set_All_Press (OB1_ID, Pressure_array_in, Calib_array_in, len, len2)


	return 0