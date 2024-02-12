// TROUBLE CONDITIONS

// https://www.alarm.com/web/system/assets/customer-ember/enums/TroubleConditionType.js

PanelAuxPanic = 4
PhoneLineCut = 9
ModemPanelCommError = 10
SensorMalfunction = 12
RadioOff = 13
ACFailure = 14
SensorLowBattery = 15
PanelLowBattery = 16
PanelNotResponding = 17
CameraNotReachable = 21
SensorTamper = 28
BroadbandCommFailure = 33
CellCommFailure = 34
DeviceDisabled = 36
SystemLocked = 44
EthernetCableUnplugged = 52
AlarmInMemory = 53
SensorBypassed = 54
ThermostatTooCold = 55
ThermostatTooWarm = 56
SmokeSensorReset = 57
HeatingAndCoolingAlert = 63
PGM2FireTrouble = 64
CarbonMonoxideSensorTrouble = 66
FreezeSensorTrouble = 67
HeatOrProbeSensorTrouble = 68
BatteryCharging = 69
BatteryAbsent = 70
WarmStartTrouble = 75
PanelOvercurrentTrouble = 76
FireSensorTrouble = 77
ZoneDeviceMaskTrouble = 78
GasTrouble = 79
RfJamTrouble = 81
NotNetworkedTrouble = 82
PanelTamper = 83
PeripheralAuxTrouble = 84
CredentialsInConflict = 85
SirenTamper = 88
SmallLeak = 95
MediumLeak = 96
LargeLeak = 97
SevereHVACAlert = 108
DevicePowerIssue = 110
InstallerResetNeeded = 113
PeriodicLeak = 121
ThermostatGroupingError = 132
RemoteResetNeeded = 133
RelayNotPowered = 138
PanelMountingTamper = 139
CellularSensorNotResponding = 140
CellularSensorBatteryMissing = 141
CellularSensorLowBattery = 144
HVACControlFailure = 148
ConfirmedBurglaryAlarm = 149
ConfirmedEmergencyAlarm = 150
DeviceCoolDownMode = 154
CommunicatorUpgradeRequired = 155
LowBusVoltage = 160
AuxSupply = 161
OutputFault = 162
BellCircuit = 163
BusFault = 164
DeviceWarmUpMode = 168
ConfigurePanelWifi = 170
LockJammed = 172
LockdownNotConfigured = 173



  /**
   * @enum {number}
   */
  const NoSubType = _exports.NoSubType = 0;
  /**
   * @enum {number}
   */
  const SensorMalfunction_GeoServices = _exports.SensorMalfunction_GeoServices = 1;
  /**
   * @enum {number}
   */
  const SensorMalfunction_LiftMaster = _exports.SensorMalfunction_LiftMaster = 2;
  /**
   * @enum {number}
   */
  const SensorMalfunction_ZWave = _exports.SensorMalfunction_ZWave = 3;
  /**
   * @enum {number}
   */
  const SensorMalfunction_Lutron = _exports.SensorMalfunction_Lutron = 4;
  /**
   * @enum {number}
   */
  const SensorMalfunction_Sensor = _exports.SensorMalfunction_Sensor = 5;
  /**
   * @enum {number}
   */
  const SensorMalfunction_Sonos = _exports.SensorMalfunction_Sonos = 6;
  /**
   * @enum {number}
   */
  const SensorMalfunction_CarConnector = _exports.SensorMalfunction_CarConnector = 7;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_ADCSmartThermostat = _exports.IncompatibleDevice_ADCSmartThermostat = 8;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_ImageSensor = _exports.IncompatibleDevice_ImageSensor = 9;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_Kwikset = _exports.IncompatibleDevice_Kwikset = 10;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_Quickbox = _exports.IncompatibleDevice_Quickbox = 11;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_RemoteTemperatureSensor = _exports.IncompatibleDevice_RemoteTemperatureSensor = 12;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_Schlage = _exports.IncompatibleDevice_Schlage = 13;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_Stelpro = _exports.IncompatibleDevice_Stelpro = 14;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_TwoWayTalkingTouchScreen = _exports.IncompatibleDevice_TwoWayTalkingTouchScreen = 15;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_Westinghouse = _exports.IncompatibleDevice_Westinghouse = 16;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_Yale = _exports.IncompatibleDevice_Yale = 17;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_ZWaveGarage = _exports.IncompatibleDevice_ZWaveGarage = 18;
  /**
   * @enum {number}
   */
  const SensorLowBattery_CarConnector = _exports.SensorLowBattery_CarConnector = 19;
  /**
   * @enum {number}
   */
  const SensorTamper_CarConnector = _exports.SensorTamper_CarConnector = 20;
  /**
   * @enum {number}
   */
  const SensorTamper_ContactSensor = _exports.SensorTamper_ContactSensor = 21;
  /**
   * @enum {number}
   */
  const SensorTamper_MotionSensor = _exports.SensorTamper_MotionSensor = 22;
  /**
   * @enum {number}
   */
  const SensorTamper_ImageSensor = _exports.SensorTamper_ImageSensor = 23;
  /**
   * @enum {number}
   */
  const ControllerPowerFault_Aero = _exports.ControllerPowerFault_Aero = 24;
  /**
   * @enum {number}
   */
  const ControllerPowerFault_Mercury = _exports.ControllerPowerFault_Mercury = 25;
  /**
   * @enum {number}
   */
  const PanelTamper_AlarmHub = _exports.PanelTamper_AlarmHub = 26;
  /**
   * @enum {number}
   */
  const SecureEnrollmentFailed_Critical = _exports.SecureEnrollmentFailed_Critical = 27;
  /**
   * @enum {number}
   */
  const SensorMalfunction_AccessPoint = _exports.SensorMalfunction_AccessPoint = 28;
  /**
   * @enum {number}
   */
  const IncompatibleDevice_IQLinearGarage = _exports.IncompatibleDevice_IQLinearGarage = 29;
  /**
   * @enum {number}
   */
  const IncompatiblePanelVersion_IQWifi6 = _exports.IncompatiblePanelVersion_IQWifi6 = 30;
  /**
   * @enum {number}
   */
  const SensorLowBattery_RechargeableVideoDevice = _exports.SensorLowBattery_RechargeableVideoDevice = 31;
  /**
   * @enum {number}
   */
  const SensorLowBattery_CriticalRechargeableVideoDevice = _exports.SensorLowBattery_CriticalRechargeableVideoDevice = 32;
  /**
   * @enum {number}
   */
  const BroadbandCommFailure_GunshotSensor = _exports.BroadbandCommFailure_GunshotSensor = 33;
  /**
   * @enum {number}
   */
  const CellCommFailure_GunshotSensor = _exports.CellCommFailure_GunshotSensor = 34;
  /**
   * @enum {number}
   */
  const CameraUnexpectedlyNotRecording_SVR = _exports.CameraUnexpectedlyNotRecording_SVR = 35;
  /**
   * @enum {number}
   */
  const CameraUnexpectedlyNotRecording_Onboard = _exports.CameraUnexpectedlyNotRecording_Onboard = 36;
  /**
   * @enum {number}
   */
  const CameraUnexpectedlyNotRecording_SVRAndOnboard = _exports.CameraUnexpectedlyNotRecording_SVRAndOnboard = 37;
