# Changelog

## [0.3.0](https://github.com/klconsultancy/ha-thermia-genesis/compare/v0.2.0...v0.3.0) (2026-11-13)


### ⚠ BREAKING CHANGES

* climate.heating (0.3.0-rc.1 only) becomes climate.thermia_genesis; the config entry migration (1.3) removes the old one.
* water_heater.hot_water and number.hot_water_start_temperature replace sensor.hot_water_start_temperature, sensor.hot_water_stop_temperature and binary_sensor.heat_pump_unit_hot_water_enabled (all disabled by default); the config entry migration (1.2) removes them.
* number.heat_pump_unit_power_consumption_control_mode and number.heat_pump_unit_input_power_limit replace the sensors of the same name (disabled by default); the config entry migration (1.2) removes them.
* the button replaces binary_sensor.heat_pump_unit_alarm_reset_pending (disabled by default); the config entry migration (1.2) removes it.
* select.thermia_genesis_operational_mode replaces sensor.thermia_genesis_operational_mode; the config entry migration (1.2) removes the sensor.
* the climate replaces sensor.heating_comfort_wheel and binary_sensor.heat_pump_unit_heating_enabled; a config entry migration (1.2) removes them. Use climate.heating instead.

### Features

* add a button that resets the alarms ([#58](https://github.com/klconsultancy/ha-thermia-genesis/issues/58)) ([09d76c6](https://github.com/klconsultancy/ha-thermia-genesis/commit/09d76c67253a9b1b0af9aed6def487d975799d44))
* add a heating climate ([#55](https://github.com/klconsultancy/ha-thermia-genesis/issues/55)) ([db9d4e9](https://github.com/klconsultancy/ha-thermia-genesis/commit/db9d4e9946f6385afa4f258fc6a48faa70fdd53b))
* enable the heating, hot water and anti-legionella demands ([#63](https://github.com/klconsultancy/ha-thermia-genesis/issues/63)) ([23bad11](https://github.com/klconsultancy/ha-thermia-genesis/commit/23bad11928c4eba49434c998fc85e6dc82ef68ce))
* put the climate on the main device ([#62](https://github.com/klconsultancy/ha-thermia-genesis/issues/62)) ([b8dbc8a](https://github.com/klconsultancy/ha-thermia-genesis/commit/b8dbc8a8fb83829c4607c382c0efaff919ccbab1))
* set power consumption control with numbers ([#59](https://github.com/klconsultancy/ha-thermia-genesis/issues/59)) ([a6ebcd0](https://github.com/klconsultancy/ha-thermia-genesis/commit/a6ebcd06f816c31c495d1b0293274f9a849ef04c))
* set the operational mode with a select ([#57](https://github.com/klconsultancy/ha-thermia-genesis/issues/57)) ([c2badfe](https://github.com/klconsultancy/ha-thermia-genesis/commit/c2badfe7a51af710dc02790dbdbfc02d1437e030))
* show the hot water as a water heater ([#60](https://github.com/klconsultancy/ha-thermia-genesis/issues/60)) ([b5e1992](https://github.com/klconsultancy/ha-thermia-genesis/commit/b5e19924e561b3bb535940f23c40cd07750614cb))
* show the Thermia brand icon ([#47](https://github.com/klconsultancy/ha-thermia-genesis/issues/47)) ([fe9f1da](https://github.com/klconsultancy/ha-thermia-genesis/commit/fe9f1da9b59aa6d612131760b8a6191b80da00f3))


### Bug Fixes

* give the water heater one target, and show the top temperature ([#64](https://github.com/klconsultancy/ha-thermia-genesis/issues/64)) ([493b2df](https://github.com/klconsultancy/ha-thermia-genesis/commit/493b2df5d1510fefd6c44fa8b39a0672938cb63f))

## [0.2.0](https://github.com/klconsultancy/ha-thermia-genesis/compare/v0.1.0...v0.2.0) (2026-11-09)


### Features

* show the heat pump unit's power in W ([#39](https://github.com/klconsultancy/ha-thermia-genesis/issues/39)) ([5ac31df](https://github.com/klconsultancy/ha-thermia-genesis/commit/5ac31df97f9ae727178817d8953a3a80427a26ee))

## 0.1.0 (2026-11-08)


### Features

* add the aggregate alarm ([#34](https://github.com/klconsultancy/ha-thermia-genesis/issues/34)) ([edfeab0](https://github.com/klconsultancy/ha-thermia-genesis/commit/edfeab0ce9941023ccf7bde5efd4c7164f3678ab))
* add the config flow with a reconfigure step ([#10](https://github.com/klconsultancy/ha-thermia-genesis/issues/10)) ([2b01568](https://github.com/klconsultancy/ha-thermia-genesis/commit/2b01568398deb273475624e91b682623cf8524da))
* add the cooling entities ([#20](https://github.com/klconsultancy/ha-thermia-genesis/issues/20)) ([fd08cd9](https://github.com/klconsultancy/ha-thermia-genesis/commit/fd08cd9ae698e1f241c2d39b53917a576c4568ec))
* add the diagnostics ([#35](https://github.com/klconsultancy/ha-thermia-genesis/issues/35)) ([62ed724](https://github.com/klconsultancy/ha-thermia-genesis/commit/62ed7244d9e46c75780131864fca5f3de00dd392))
* add the electric meter entities ([#29](https://github.com/klconsultancy/ha-thermia-genesis/issues/29)) ([1d76efd](https://github.com/klconsultancy/ha-thermia-genesis/commit/1d76efd7eedf12b86530192ab96016793f470da3))
* add the energy statistics entities ([#31](https://github.com/klconsultancy/ha-thermia-genesis/issues/31)) ([a916237](https://github.com/klconsultancy/ha-thermia-genesis/commit/a91623728cbb027e66e999b67f3300dd97bc311c))
* add the heat pump unit's entities ([#15](https://github.com/klconsultancy/ha-thermia-genesis/issues/15)) ([1203a6f](https://github.com/klconsultancy/ha-thermia-genesis/commit/1203a6fbafa62c1a9bc51d61c8ac981b64506976))
* add the heating entities ([#16](https://github.com/klconsultancy/ha-thermia-genesis/issues/16)) ([a94c126](https://github.com/klconsultancy/ha-thermia-genesis/commit/a94c1262688076ecbf24f473f904596a67f55abd))
* add the hot water and hot gas heat recovery entities ([#18](https://github.com/klconsultancy/ha-thermia-genesis/issues/18)) ([f95c9ad](https://github.com/klconsultancy/ha-thermia-genesis/commit/f95c9ad6415c6dc6d03d0ad51ee1e816f3904b41))
* add the mix valve 1 entities ([#17](https://github.com/klconsultancy/ha-thermia-genesis/issues/17)) ([c06dc66](https://github.com/klconsultancy/ha-thermia-genesis/commit/c06dc661de27756ae9eb4713a34a353b182114fb))
* add the pool entities ([#28](https://github.com/klconsultancy/ha-thermia-genesis/issues/28)) ([eaf2e44](https://github.com/klconsultancy/ha-thermia-genesis/commit/eaf2e4489b98f31e606be2f0a5852ae863cc7b23))
* add the sensor and binary sensor platforms with the status entities ([#14](https://github.com/klconsultancy/ha-thermia-genesis/issues/14)) ([6acfd18](https://github.com/klconsultancy/ha-thermia-genesis/commit/6acfd1821fa86778c4135d307a40048760bb1a7b))
* set up the pump with a coordinator, devices and a firmware repair issue ([#12](https://github.com/klconsultancy/ha-thermia-genesis/issues/12)) ([89d046c](https://github.com/klconsultancy/ha-thermia-genesis/commit/89d046c336425f05950038c0a50c56359576b666))


### Bug Fixes

* name the continuous brine and condenser pumps alike in Dutch ([#37](https://github.com/klconsultancy/ha-thermia-genesis/issues/37)) ([841adb1](https://github.com/klconsultancy/ha-thermia-genesis/commit/841adb19606b80ee4b458dd694a96999fd2c3ced))
* say compressortrap in the Dutch gear names of the heat pump unit ([#19](https://github.com/klconsultancy/ha-thermia-genesis/issues/19)) ([baf900b](https://github.com/klconsultancy/ha-thermia-genesis/commit/baf900b84b774ba8874954e9ffb49ed45cfdc1e0))
* use Home Assistant's Dutch wording for diagnostics in the firmware repair ([#36](https://github.com/klconsultancy/ha-thermia-genesis/issues/36)) ([dbe3ada](https://github.com/klconsultancy/ha-thermia-genesis/commit/dbe3adafd7396a5502641bc004544a07bfd3fa23))
