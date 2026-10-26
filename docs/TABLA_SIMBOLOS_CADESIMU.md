# Catálogo Maestro de Símbolos y Keycodes CADe SIMU

Extracción exhaustiva realizada mediante ingeniería inversa vía **REA** (Resource Extraction & Binary Analysis) sobre el ejecutable original `CADe_SIMU_V4.2.exe` y análisis de los 18 esquemas `.cad` de ejemplo (incluyendo `all_simbol.cad`, `allpart2.cad`, `all4.cad`, `all5.cad`, `2D.cad`, `3D.cad` y laboratorios virtuales).

- **Total de Keycodes / Type IDs únicos detectados**: 343
- **Familias cubiertas**: Alimentaciones, Motores, Contactores, Protecciones, Contactos Auxiliares y Temporizados, Accionamientos, Detectores, Bobinas y Señalización, Lógica Digital, Ladder, GRAFCET, PLCs (LOGO!, S7-1200, S7-1500, ET-200, Arduino), Actuadores Neumáticos, Cables, 2D/3D y Maquetas Virtuales.

## Alimentaciones (21 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `3000` | **Alimentación Fase** | `alimentacion_fase` | `-X` | `-` | 7 veces (7 files) | Borne de alimentación de Fase (L) |
| `3001` | **Alimentación Neutro** | `alimentacion_neutro` | `-X` | `-` | 7 veces (7 files) | Borne de alimentación de Neutro (N) |
| `3002` | **Alimentación Protección** | `alimentacion_proteccion` | `-X` | `-` | 3 veces (3 files) | Borne de toma de tierra / conductor de protección (PE) |
| `3003` | **Alimentación F+N** | `alimentacion_f_n` | `-X` | `-` | 7 veces (5 files) | Alimentación monofásica compuesta Fase + Neutro |
| `3004` | **Alimentación L1+L2+L3** | `alimentacion_3p` | `-X` | `-` | 4 veces (4 files) | Alimentación trifásica 3 líneas (L1, L2, L3) |
| `3005` | **Alimentación L1+L2+L3+PE** | `alimentacion_3p_pe` | `-X` | `-` | 7 veces (7 files) | Alimentación trifásica con tierra (L1, L2, L3 + PE) |
| `3006` | **Alimentación L1+L2+L3+N** | `alimentacion_3p_n` | `-X` | `-` | 2 veces (2 files) | Alimentación trifásica con neutro (L1, L2, L3 + N) |
| `3007` | **Alimentación L1+L2+L3+N+PE** | `alimentacion_3p_n_pe` | `-X` | `-` | 2 veces (2 files) | Alimentación trifásica completa con neutro y tierra |
| `3008` | **Alimentación +** | `alimentacion_positiva` | `-X` | `-` | 4 veces (4 files) | Borne de alimentación de corriente continua positiva (+) |
| `3009` | **Alimentación -** | `alimentacion_negativa` | `-X` | `-` | 4 veces (4 files) | Borne de alimentación de corriente continua negativa (-) |
| `3010` | **Alimentación +-** | `alimentacion_dc_dual` | `-X` | `-` | 1 veces (1 files) | Fuente de alimentación continua dual (+ -) |
| `3011` | **Alimentación F+N+PE** | `alimentacion_f_n_pe` | `-X` | `-` | 1 veces (1 files) | Alimentación monofásica con neutro y tierra |
| `3012` | **Transformador** | `transformador_1p` | `-T` | `1-2-3-4` | 1 veces (1 files) | Transformador monofásico reductor/elevador |
| `3013` | **Rectificador** | `puente_rectificador` | `-V` | `1-2-3-4` | 1 veces (1 files) | Puente rectificador de diodos monofásico de onda completa |
| `3014` | **Fuente de alimentación** | `fuente_alimentacion_1p` | `-V` | `1-2-3-4-PE` | 1 veces (1 files) | Fuente conmutada / estabilizada monofásica CA/CC |
| `3015` | **Alimentación Protección** | `toma_tierra` | `-` | `-` | 1 veces (1 files) | Símbolo de toma de tierra de protección |
| `3016` | **Diodo** | `diodo` | `-D` | `1-2` | 1 veces (1 files) | Diodo semiconductor / rectificador unipolar |
| `3017` | **Transformador III** | `transformador_3p` | `-T` | `1-2-3-4-5-6` | 1 veces (1 files) | Transformador trifásico de potencia |
| `3018` | **Fuente de alimentación III** | `fuente_alimentacion_3p` | `-V` | `1-2-3-4-5-PE` | 1 veces (1 files) | Fuente de alimentación trifásica CA/CC |
| `3019` | **Bateria** | `bateria` | `-V` | `+--` | 1 veces (1 files) | Batería / Acumulador de corriente continua |
| `3020` | **Toma de corriente** | `toma_corriente` | `-TC` | `-` | 1 veces (1 files) | Base de enchufe / toma de corriente Schuko |

## Motores (14 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `1000` | **Motor trifásico** | `motor_trifasico` | `-M` | `U1-V1-W1-PE` | 16 veces (14 files) | Motor trifásico estándar asíncrono (jaula de ardilla) |
| `1001` | **Motor trifásico YD** | `motor_trifasico_yd` | `-M` | `U1-V1-W1-PE-W2-U2-V2` | 3 veces (3 files) | Motor trifásico estrella-triángulo (6 bornes U1,V1,W1,U2,V2,W2) |
| `1002` | **Motor monofásico** | `motor_monofasico` | `-M` | `U1-V1-PE` | 1 veces (1 files) | Motor monofásico corriente alterna |
| `1003` | **Motor Dahalander** | `motor_dahlander` | `-M` | `U1-V1-W1-PE-U2-V2-W2` | 1 veces (1 files) | Motor de dos velocidades por conmutación de polos (Dahlander) |
| `1004` | **Motor rotor bobinado** | `motor_rotor_bobinado` | `-M` | `U1-V1-W1-PE-K-L-M` | 1 veces (1 files) | Motor trifásico de rotor bobinado con anillos rozantes |
| `1005` | **Motor Dos velocidades** | `motor_dos_velocidades` | `-M` | `U1-V1-W1-PE-U2-V2-W2` | 1 veces (1 files) | Motor de dos velocidades con devanados independientes |
| `1006` | **Motor cc. Iman P.** | `motor_cc_iman` | `-M` | `A1-A2-PE` | 1 veces (1 files) | Motor de corriente continua de imanes permanentes |
| `1007` | **Motor cc. Indep.** | `motor_cc_indep` | `-M` | `A1-A2-PE-F1-F2` | 1 veces (1 files) | Motor de corriente continua con excitación independiente |
| `1008` | **Motor monofásico con condensador** | `motor_monofasico_cond` | `-M` | `U1-V1-PE-U2-V2` | 1 veces (1 files) | Motor monofásico con condensador de arranque y disyuntor centrífugo |
| `1009` | **Freno** | `freno` | `-Fr` | `U1-V1-PE` | 1 veces (1 files) | Freno electromagnético para motor |
| `1010` | **Motor trifásico como monofásico** | `motor_trifasico_como_monofasico` | `-M` | `U1-V1-W1-PE` | 1 veces (1 files) | Conexión Steinmetz para motor trifásico en red monofásica |
| `1011` | **Motor paso a paso unipolar** | `motor_paso_paso_unipolar` | `-M` | `1-2-3-4-5-6` | 1 veces (1 files) | Motor paso a paso unipolar de 4/5 hilos |
| `1012` | **Motor paso a paso bipolar** | `motor_paso_paso_bipolar` | `-M` | `1-2-3-4` | 1 veces (1 files) | Motor paso a paso bipolar de 4 hilos |
| `10550` | **Actuador lineal eléctrico** | `actuador_lineal_electrico` | `-M` | `50-50--FC2--FC1-000.025.050.075.100.-G   .0.-M   .0--MD` | 1 veces (1 files) | Cilindro / husillo actuador eléctrico lineal |

## Contactores (10 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `2000` | **Contactor II** | `contactor_2p` | `-KM` | `1-3-2-4` | 1 veces (1 files) | Contactor de potencia bipolar (2 polos de fuerza) |
| `2001` | **Contactor III** | `contactor_3p` | `-KM1,-K1,-KM,K1,-K2` | `1-3-5-2-4-6` | 16 veces (12 files) | Contactor de potencia tripolar (3 polos de fuerza) |
| `2002` | **Contactor IIII** | `contactor_4p` | `-KM` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Contactor de potencia tetrapolar (4 polos de fuerza) |
| `2003` | **Interruptor II** | `interruptor_potencia_2p` | `-S` | `1-3-2-4` | 1 veces (1 files) | Interruptor seccionador de carga bipolar |
| `2004` | **Interruptor III** | `interruptor_potencia_3p` | `-S` | `1-3-5-2-4-6` | 1 veces (1 files) | Interruptor seccionador de carga tripolar |
| `2005` | **Interruptor IIII** | `interruptor_potencia_4p` | `-S` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Interruptor seccionador de carga tetrapolar |
| `2006` | **Contactor I** | `contactor_1p` | `-KM1,-KM,-Q1,-KM2,-KM3` | `1-2` | 6 veces (5 files) | Contactor de potencia unipolar (1 polo de fuerza) |
| `2007` | **Interruptor I** | `interruptor_potencia_1p` | `-S` | `1-2` | 1 veces (1 files) | Interruptor seccionador unipolar |
| `2008` | **Contactor III conmutador** | `contactor_inversor_3p` | `-KM` | `1-3-5-2-4-6` | 1 veces (1 files) | Contactor inversor conmutado tripolar |
| `2009` | **Enclavamiento** | `enclavamiento_mecanico` | `-KM1` | `-KM2` | 1 veces (1 files) | Enclavamiento mecánico entre dos contactores |

## Protecciones (25 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `5000` | **Fusible I** | `fusible_1p` | `-F2,-F` | `1-2` | 3 veces (3 files) | Fusible de protección unipolar (1P) |
| `5001` | **Fusible IN** | `fusible_1p_n` | `-F` | `1-3-2-4` | 1 veces (1 files) | Fusible unipolar más seccionador neutro (1P+N) |
| `5002` | **Fusible II** | `fusible_2p` | `-F` | `1-3-2-4` | 1 veces (1 files) | Fusibles bipolares (2P) |
| `5003` | **Fusible III** | `fusible_3p` | `-F1,-F` | `1-3-5-2-4-6` | 3 veces (3 files) | Fusibles tripolares de potencia (3P) |
| `5004` | **Fusible IIIN** | `fusible_3p_n` | `-F` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Fusibles tripolares más neutro (3P+N) |
| `5005` | **Fusible seccionable I** | `seccionador_fusible_1p` | `-F` | `1-2` | 1 veces (1 files) | Seccionador portafusible unipolar |
| `5006` | **Fusible seccionable IN** | `seccionador_fusible_1p_n` | `-F` | `1-3-2-4` | 1 veces (1 files) | Seccionador portafusible 1P+N |
| `5007` | **Fusible seccionable II** | `seccionador_fusible_2p` | `-F` | `1-3-2-4` | 1 veces (1 files) | Seccionador portafusible bipolar (2P) |
| `5008` | **Fusible seccionable III** | `seccionador_fusible_3p` | `-F` | `1-3-5-2-4-6` | 3 veces (3 files) | Seccionador portafusible tripolar (3P) |
| `5009` | **Fusible seccionable IIIN** | `seccionador_fusible_3p_n` | `-F` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Seccionador portafusible tetrapolar (3P+N) |
| `6000` | **Automático I** | `automatico_1p` | `-F` | `1-2` | 1 veces (1 files) | Interruptor magnetotérmico unipolar (PIA 1P) |
| `6001` | **Automático IN** | `automatico_1p_n` | `-F` | `1-3-2-4` | 1 veces (1 files) | Interruptor magnetotérmico 1P+N |
| `6002` | **Automático II** | `automatico_2p` | `-F` | `1-3-2-4` | 4 veces (2 files) | Interruptor magnetotérmico bipolar (PIA 2P) |
| `6003` | **Automático III** | `automatico_3p` | `-F` | `1-3-5-2-4-6` | 1 veces (1 files) | Interruptor magnetotérmico tripolar (PIA 3P) |
| `6004` | **Automático IIIN** | `automatico_3p_n` | `-F` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Interruptor magnetotérmico tetrapolar (PIA 3P+N) |
| `6005` | **Diferencial IN** | `diferencial_1p_n` | `-F` | `1-3-2-4` | 1 veces (1 files) | Interruptor diferencial bipolar (ID 2P / 1P+N) |
| `6006` | **Diferencial IIIN** | `diferencial_3p_n` | `-F` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Interruptor diferencial tetrapolar (ID 4P / 3P+N) |
| `6007` | **Relé Térmico** | `rele_termico_potencia` | `-F,-F3,F3,-F1,-F2` | `1-3-5-2-4-6` | 17 veces (10 files) | Relé térmico bimetálico de potencia (bloque de 3 bimetales) |
| `6008` | **Disyuntor I** | `disyuntor_1p` | `-F2,-F1,-Q` | `1-3-2-4` | 3 veces (3 files) | Disyuntor / Guardamotor unipolar |
| `6009` | **Disyuntor IN** | `disyuntor_1p_n` | `-Q1,F2,-Q,-F1,-F2` | `1-3-5-2-4-6` | 11 veces (9 files) | Disyuntor / Guardamotor 1P+N |
| `6010` | **Disyuntor II** | `disyuntor_2p` | `-Q,F1,-Q1` | `1-2` | 4 veces (4 files) | Disyuntor / Guardamotor bipolar |
| `6011` | **Disyuntor III** | `disyuntor_3p` | `-Q` | `1-3-2-4` | 2 veces (2 files) | Disyuntor guardamotor magnetotérmico tripolar de motor |
| `6012` | **Disyuntor IIIN** | `disyuntor_3p_n` | `-Q` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Disyuntor tetrapolar 3P+N |
| `6013` | **Limitador sobretensiones IN** | `limitador_sobretensiones_1p_n` | `-F` | `1-2-3` | 1 veces (1 files) | Descargador de sobretensiones transitorias monofásico |
| `6014` | **Limitador sobretensiones IIIN** | `limitador_sobretensiones_3p_n` | `-F` | `1-2-3-4-5` | 1 veces (1 files) | Descargador de sobretensiones transitorias trifásico |

## Contactos (15 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `7000` | **Contacto NA** | `contacto_aux_na` | `-K,-KM1,-KM2,K1,-K1` | `13-14` | 16 veces (7 files) | Contacto auxiliar normalmente abierto (13-14 / 3-4) |
| `7001` | **Contacto NC** | `contacto_aux_nc` | `-KM1,K1,-K,-KM2` | `11-12` | 5 veces (4 files) | Contacto auxiliar normalmente cerrado (11-12 / 1-2) |
| `7002` | **Contacto NA+NC** | `contacto_aux_na_nc` | `-K` | `11-13-12-14` | 1 veces (1 files) | Doble contacto auxiliar NA + NC |
| `7003` | **Contacto CON** | `contacto_aux_con` | `-K` | `11-12-14` | 1 veces (1 files) | Contacto auxiliar conmutado (11-12-14) |
| `7004` | **Con. Conexión NA** | `contacto_temp_on_delay_na` | `-KA,-T1,-T3,-T2,-T4` | `67-68` | 5 veces (2 files) | Contacto temporizado al trabajo NA (ON Delay NO) |
| `7005` | **Con. Conexión NC** | `contacto_temp_on_delay_nc` | `-KA` | `55-56` | 1 veces (1 files) | Contacto temporizado al trabajo NC (ON Delay NC) |
| `7006` | **Con. Conexión NA+NC** | `contacto_temp_on_delay_na_nc` | `-KA` | `55-57-56-58` | 1 veces (1 files) | Contacto temporizado al trabajo NA + NC |
| `7007` | **Con. Conexión CON** | `contacto_temp_on_delay_con` | `-KA` | `55-56-58` | 1 veces (1 files) | Contacto temporizado al trabajo conmutado |
| `7008` | **Con. Desconexión NA** | `contacto_temp_off_delay_na` | `-KA` | `67-68` | 1 veces (1 files) | Contacto temporizado al reposo NA (OFF Delay NO) |
| `7009` | **Con. Desconexión NC** | `contacto_temp_off_delay_nc` | `-KA` | `55-56` | 1 veces (1 files) | Contacto temporizado al reposo NC (OFF Delay NC) |
| `7010` | **Con. Desconexión NA+NC** | `contacto_temp_off_delay_na_nc` | `-KA` | `55-57-56-58` | 1 veces (1 files) | Contacto temporizado al reposo NA + NC |
| `7011` | **Con. Desconexión CON** | `contacto_temp_off_delay_con` | `-KA` | `55-56-58` | 1 veces (1 files) | Contacto temporizado al reposo conmutado |
| `7013` | **Conexión Desconexión NA** | `contacto_temp_on_off_na` | `-KA` | `55-56` | 2 veces (1 files) | Contacto temporizado conexión-desconexión NA |
| `7014` | **Conexión Desconexión NC** | `contacto_temp_on_off_nc` | `-KA` | `55-57-56-58` | 1 veces (1 files) | Contacto temporizado conexión-desconexión NC |
| `7015` | **Conexión Desconexión NA+NC** | `contacto_temp_on_off_na_nc` | `-KA` | `55-56-58` | 1 veces (1 files) | Contacto temporizado conexión-desconexión NA+NC |

## Accionamientos (24 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `8000` | **Pulsador NA** | `pulsador_na` | `-S1,S2,-S2,-S,-S3` | `13-14` | 19 veces (11 files) | Pulsador normalmente abierto (marcha) |
| `8001` | **Pulsador NC** | `pulsador_nc` | `-S2,-S1,-S,S1,-P` | `11-12` | 9 veces (8 files) | Pulsador normalmente cerrado (paro) |
| `8002` | **Pulsador NA-NC** | `pulsador_na_nc` | `-S,-S1,-S2` | `11-13-12-14` | 3 veces (2 files) | Pulsador de doble contacto NA + NC |
| `8003` | **Pulsador CON** | `pulsador_con` | `-S` | `11-12-14` | 1 veces (1 files) | Pulsador con contacto conmutado |
| `8004` | **Pulsador seta NA** | `pulsador_seta_na` | `-S` | `13-14` | 1 veces (1 files) | Pulsador de seta de emergencia NA |
| `8005` | **Pulsador seta NC** | `pulsador_seta_nc` | `-S,-PE` | `11-12` | 2 veces (2 files) | Pulsador de seta con enclavamiento / parada de emergencia NC |
| `8006` | **Pulsador seta NA-NC** | `pulsador_seta_na_nc` | `-S` | `11-13-12-14` | 1 veces (1 files) | Pulsador de seta de emergencia NA + NC |
| `8007` | **Pulsador seta CON** | `pulsador_seta_con` | `-S` | `11-12-14` | 1 veces (1 files) | Pulsador de seta con contacto conmutado |
| `8008` | **Interruptor NA** | `interruptor_na` | `-S` | `13-14` | 1 veces (1 files) | Interruptor mantenido NA |
| `8009` | **Interruptor NC** | `interruptor_nc` | `-S` | `11-12` | 1 veces (1 files) | Interruptor mantenido NC |
| `8010` | **Interruptor NA-NC** | `interruptor_na_nc` | `-S` | `11-13-12-14` | 1 veces (1 files) | Interruptor mantenido NA + NC |
| `8011` | **Interruptor CON** | `interruptor_con` | `-S` | `11-12-14` | 1 veces (1 files) | Interruptor mantenido conmutado |
| `8012` | **Final de carrera NA** | `final_carrera_na` | `-S` | `13-14` | 1 veces (1 files) | Interruptor de posición / fin de carrera mecánico NA |
| `8013` | **Final de carrera NC** | `final_carrera_nc` | `-S` | `11-12` | 1 veces (1 files) | Interruptor de posición / fin de carrera mecánico NC |
| `8014` | **Final de carrera NA-NC** | `final_carrera_na_nc` | `-S` | `11-13-12-14` | 1 veces (1 files) | Final de carrera con contacto NA + NC |
| `8015` | **Final de carrera COM** | `final_carrera_com` | `-S` | `11-12-14` | 1 veces (1 files) | Final de carrera con contacto conmutado |
| `8016` | **Térmico NA** | `contacto_termico_na` | `-F3,-F,-F1,-F2` | `97-98` | 5 veces (3 files) | Contacto auxiliar de relé térmico NA (97-98 señalización) |
| `8017` | **Térmico NC** | `contacto_termico_nc` | `-F3,-F1,F3,-F,-F2` | `95-96` | 7 veces (5 files) | Contacto auxiliar de relé térmico NC (95-96 disparo/paro) |
| `8018` | **Térmico NA-NC** | `contacto_termico_na_nc` | `-F3,-F,-F1` | `95-97-96-98` | 4 veces (4 files) | Contactos auxiliares térmicos NA + NC (95-96 y 97-98) |
| `8019` | **Térmico CON** | `contacto_termico_con` | `F3,-F` | `95-96-98` | 2 veces (2 files) | Contacto auxiliar térmico conmutado (95-96-98) |
| `8020` | **Conmutador I-0-II** | `conmutador_1_0_2` | `-S` | `1-2-3` | 1 veces (1 files) | Selector rotativo con posición cero central (1 - 0 - 2) |
| `8021` | **Conmutador I-II-III** | `conmutador_1_2_3` | `-S` | `1-2-3-4` | 1 veces (1 files) | Selector rotativo de 3 posiciones |
| `8022` | **Conmutador cruce** | `conmutador_cruce` | `-S` | `1-2-3-4` | 1 veces (1 files) | Conmutador de cruzamiento eléctrico |
| `8023` | **Botón pulsador** | `boton_pulsador` | `-S` | `0` | 1 veces (1 files) | Pulsador electromecánico empotrado |

## Detectores (16 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `7500` | **Det. inductivo NA** | `sensor_inductivo_na` | `-B` | `1-2` | 1 veces (1 files) | Sensor de proximidad inductivo normalmente abierto |
| `7506` | **Det. capacitivo NA** | `sensor_capacitivo_na` | `-B` | `1-2` | 1 veces (1 files) | Sensor de proximidad capacitivo normalmente abierto |
| `7512` | **Det. magnético NA** | `sensor_magnetico_na` | `-B` | `1-2` | 1 veces (1 files) | Detector magnético / interruptor reed normalmente abierto |
| `7520` | **Det. inductivo NC** | `sensor_inductivo_nc` | `-B` | `1-2` | 1 veces (1 files) | Sensor de proximidad inductivo normalmente cerrado |
| `7526` | **Det. capacitivo NC** | `sensor_capacitivo_nc` | `-B` | `1-2` | 1 veces (1 files) | Sensor de proximidad capacitivo normalmente cerrado |
| `7532` | **Det. magnético NC** | `sensor_magnetico_nc` | `-B` | `1-2` | 1 veces (1 files) | Detector magnético / interruptor reed normalmente cerrado |
| `7550` | **Barrera fotoeléctrica** | `fotocelula_barrera` | `-B` | `1-2-3-4-5` | 1 veces (1 files) | Fotocélula / Sensor óptico completo |
| `7551` | **Barrera emisor** | `fotocelula_emisor` | `-B` | `1-2` | 1 veces (1 files) | Emisor de barrera óptica |
| `7553` | **Barrera receptor NA** | `fotocelula_receptor_na` | `-B` | `1-2` | 1 veces (1 files) | Receptor de barrera óptica NA |
| `7559` | **Barrera receptor NC** | `fotocelula_receptor_nc` | `-B` | `1-2` | 1 veces (1 files) | Receptor de barrera óptica NC |
| `7570` | **Presostato NA** | `presostato_na` | `-B` | `1-2` | 1 veces (1 files) | Sensor de presión / presostato contacto NA |
| `7576` | **Vacuostato NA** | `vacuostato_na` | `-B` | `1-2` | 1 veces (1 files) | Sensor de vacío / vacuostato contacto NA |
| `7582` | **Presostato NC** | `presostato_nc` | `-B` | `1-2` | 1 veces (1 files) | Sensor de presión / presostato contacto NC |
| `7588` | **Vacuostato NC** | `vacuostato_nc` | `-B` | `1-2` | 1 veces (1 files) | Sensor de vacío / vacuostato contacto NC |
| `7594` | **Termostato NA** | `termostato_na` | `-B` | `1-2` | 1 veces (1 files) | Sensor térmico / termostato de temperatura NA |
| `7600` | **Termostato NC** | `termostato_nc` | `-B` | `1-2` | 1 veces (1 files) | Sensor térmico / termostato de temperatura NC |

## Bobinas (11 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `9000` | **Bobina** | `bobina_contactor` | `-K,-KM1,-K1,K1,-K2` | `A1-A2` | 18 veces (12 files) | Bobina monoestable estándar para contactor o relé (A1-A2) |
| `9001` | **Bobina biestable** | `bobina_biestable` | `-K` | `A1-B1-A2` | 1 veces (1 files) | Bobina de relé biestable con doble devanado (Set/Reset) |
| `9002` | **Telerruptor** | `telerruptor` | `-K` | `A1-A2` | 1 veces (1 files) | Relé de impulsos telerruptor |
| `9003` | **Bobina electroválvula** | `bobina_electrovalvula` | `-EV  ` | `A1-A2` | 1 veces (1 files) | Solenoide de electroválvula hidráulica o neumática |
| `9004` | **Temp. conexión** | `temp_conexion_bobina` | `-K,-T3,-T4,-T1,-T2` | `A1-A2-0-1; A1-A2-1-1` | 5 veces (2 files) | Bobina de relé temporizado a la conexión (ON Delay A1-A2) |
| `9005` | **Temp. desconexión** | `temp_desconexion_bobina` | `-K` | `A1-A2-0-1` | 1 veces (1 files) | Bobina de relé temporizado a la desconexión (OFF Delay A1-A2) |
| `9006` | **Temp. conexión desconexión** | `temp_on_off_bobina` | `-K` | `A1-A2-0-1` | 1 veces (1 files) | Bobina temporizada conexión-desconexión |
| `9007` | **Relé intermitente** | `rele_intermitente` | `-K` | `A1-A2-0-1` | 1 veces (1 files) | Relé intermitente de destellos cíclicos |
| `9014` | **Interruptor horario** | `interruptor_horario` | `-K` | `A1-A2-0-0-0-0-0-0` | 1 veces (1 files) | Reloj programador horario diario/semanal |
| `9015` | **Generador de pulsos** | `generador_pulsos` | `-K` | `A1-A2-0-1-0-1` | 1 veces (1 files) | Generador de tren de pulsos periódicos |
| `9016` | **Contador de pulsos** | `contador_pulsos_bobina` | `-C` | `A1-C-D-R-0-0-A2` | 1 veces (1 files) | Bobina de avance de contador electromecánico |

## Senalizacion (6 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `9008` | **Piloto señalización** | `piloto_senializacion` | `-H,-H1,-H2,-H3,H1` | `X1-X2-1; X1-X2-0; X1-X2-2` | 20 veces (7 files) | Lámpara piloto de señalización luminosa continua |
| `9009` | **Piloto intermitente** | `piloto_intermitente` | `-H` | `X1-X2-0` | 1 veces (1 files) | Lámpara piloto con destello intermitente |
| `9010` | **Timbre** | `timbre` | `-H` | `X1-X2` | 1 veces (1 files) | Avisador acústico timbre electromecánico |
| `9011` | **Zumbador** | `zumbador` | `-H` | `X1-X2` | 1 veces (1 files) | Zumbador piezoeléctrico / buzzer acústico |
| `9012` | **Sirena** | `sirena` | `-H` | `X1-X2` | 1 veces (1 files) | Sirena acústica de alarma |
| `9013` | **Bocina** | `bocina` | `-H` | `X1-X2` | 1 veces (1 files) | Bocina o claxon acústico industrial |

## Potencia (12 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `1070` | **Resistencia I** | `resistencia_1p` | `-K` | `A1-A2-1-2` | 1 veces (1 files) | Banco de resistencia monofásica de frenado o calefactora |
| `1071` | **Resistencia III** | `resistencia_3p` | `-K` | `A1-A2-1-2` | 1 veces (1 files) | Banco de resistencias trifásicas estatóricas/rotóricas |
| `1072` | **Autotransformador III** | `autotransformador_3p` | `-K` | `1-3-5-2-4-6-A1-A2` | 1 veces (1 files) | Autotransformador trifásico para arranque a tensión reducida |
| `1073` | **Arrancador electrónico c.a.** | `arrancador_electronico_ca` | `-K` | `1-3-5-2-4-6-A1-A2-A3` | 2 veces (1 files) | Etapa de potencia de arrancador suave (Soft Starter) |
| `1074` | **Variador velocidad c.c. II** | `variador_velocidad_cc_2p` | `-K` | `A1-A2-13-14` | 1 veces (1 files) | Variador de velocidad CC monofásico / bifásico |
| `1075` | **Variador velocidad c.c. III** | `variador_velocidad_cc_3p` | `-K` | `A1-A2-12-11-14` | 1 veces (1 files) | Variador de velocidad CC trifásico |
| `9040` | **Control arrancador electrónico c.a.** | `control_arrancador_suave` | `-K` | `L1-L2-L3-N` | 1 veces (1 files) | Módulo de control para arrancador suave |
| `9041` | **Control inversor electrónico c.a.** | `control_inversor_electronico` | `-K` | `L1-L2-L3` | 1 veces (1 files) | Módulo de control de inversión electrónica |
| `9042` | **Control Variador velocidad c.a.** | `control_variador_ca` | `-K` | `L1-L2-L3` | 1 veces (1 files) | Módulo de maniobra de variador de frecuencia CA |
| `9043` | **Control Variador velocidad c.c.** | `control_variador_cc` | `-K` | `L1-L2-L3` | 1 veces (1 files) | Módulo de maniobra de regulador de velocidad CC |
| `9044` | **Variador velocidad c.a. II** | `variador_potencia_ca_2p` | `-F` | `1-3-2-4-A1-A2` | 1 veces (1 files) | Etapa de potencia de variador CA monofásico |
| `9045` | **Variador velocidad c.a. III** | `variador_potencia_ca_3p` | `-F` | `1-3-5-7-2-4-6-8` | 1 veces (1 files) | Etapa de potencia de variador CA trifásico |

## Logica (25 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `10000` | **AND** | `puerta_and` | `-U` | `-` | 1 veces (1 files) | Puerta lógica AND de 2 o más entradas |
| `10010` | **OR** | `puerta_or` | `-U` | `-` | 1 veces (1 files) | Puerta lógica OR de 2 o más entradas |
| `10020` | **EXOR** | `puerta_exor` | `-U` | `-` | 1 veces (1 files) | Puerta lógica XOR (Or exclusiva) |
| `10030` | **NAND** | `puerta_nand` | `-U` | `-` | 1 veces (1 files) | Puerta lógica NAND |
| `10040` | **INV** | `puerta_inv` | `-U` | `-` | 1 veces (1 files) | Puerta lógica inversora NOT |
| `10041` | **INV / Buffer** | `puerta_buffer` | `-U` | `-` | 1 veces (1 files) | Puerta lógica Buffer / inversora alternativa |
| `10063` | **Generatore di impulsi** | `generador_pulsos_logico` | `-C` | `R-C-D-Q-0-0` | 2 veces (1 files) | Generador de reloj de pulsos lógicos (Clock) |
| `10064` | **NOR** | `puerta_nor` | `-U` | `S-R-Q` | 2 veces (1 files) | Puerta lógica NOR |
| `10065` | **Biestable** | `biestable_rs` | `-U` | `S-R-Q` | 2 veces (1 files) | Biestable / Flip-Flop RS digital |
| `10066` | **Divisor Binario** | `divisor_binario` | `-T` | `IN-Q-0-1` | 2 veces (1 files) | Divisor de frecuencia binario digital (T-Flip Flop) |
| `10067` | **Temporizador pulso conexión** | `temporizador_pulso_digital` | `-T` | `IN-Q-0-1` | 2 veces (1 files) | Temporizador monostable de pulso digital |
| `10068` | **Temporizador desconexión** | `temporizador_desconexion_digital` | `-T` | `IN-Q-0-1` | 2 veces (1 files) | Temporizador digital a la desconexión (TOF) |
| `10069` | **Temporizador intermitente** | `temporizador_intermitente_digital` | `-T` | `IN-Q-0-1-0-1` | 2 veces (1 files) | Temporizador oscilador intermitente digital |
| `10070` | **Prueba** | `prueba_entrada_logica` | `-I` | `-` | 1 veces (1 files) | Sonda / interruptor de inyección de nivel lógico (0/1) |
| `10071` | **Visualiza** | `visualiza_salida_logica` | `-Q` | `-` | 1 veces (1 files) | Sonda indicadora de estado lógico (LED digital) |
| `10072` | **Display BCD** | `display_bcd` | `-D` | `a-b-0-c-d` | 1 veces (1 files) | Display numérico digital decodificador BCD |
| `10073` | **Display 7 Seg.** | `display_7_seg` | `-D` | `a-b-0-c-d-e-f-g` | 1 veces (1 files) | Display visualizador de 7 segmentos |
| `10074` | **Preselector** | `preselector_digital` | `-D` | `1-2-4-8-C` | 1 veces (1 files) | Rueda preselectora BCD digital manual |
| `10075` | **Contador** | `contador_digital` | `-C` | `+---R-Q-0-0-L` | 2 veces (1 files) | Contador digital de impulsos |
| `10077` | **Contador ascendente-descendente** | `contador_asc_desc` | `-C` | `14-1-2-3-12-9-8-11` | 1 veces (1 files) | Contador bidireccional digital (Up/Down) |
| `10078` | **Contador 4 bits** | `contador_4_bits` | `-C` | `1-2-3-4-5-6` | 1 veces (1 files) | Contador binario síncrono de 4 bits |
| `10080` | **Decodificador 7 segmentos** | `decodificador_7_seg` | `-C` | `7-1-2-6-13-12-11-10` | 1 veces (1 files) | Decodificador integrado BCD a 7 segmentos |
| `10081` | **Temporizador conexión** | `temporizador_conexion_digital` | `-T` | `IN-Q-0-1` | 1 veces (1 files) | Temporizador digital a la conexión (TON) |
| `10082` | **Contador 4 bits decadas** | `contador_4_bits_decadas` | `-C` | `15-1-10-9-14-4-5-11` | 2 veces (1 files) | Contador de décadas módulo 10 |
| `10083` | **Contador 4 bits ASC/DES** | `contador_4_bits_asc_des` | `-C` | `14-13-15-3-2-4-7-10` | 1 veces (1 files) | Contador de 4 bits Up/Down configurable |

## Ladder (8 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `10050` | **NA** | `ladder_contacto_na` | `I3,Q1,I1,-I1,-I3` | `-` | 7 veces (3 files) | Contacto normalmente abierto en lenguaje Ladder (LD) |
| `10051` | **NC** | `ladder_contacto_nc` | `I2,Q1,I1,-I2,-U` | `-` | 5 veces (3 files) | Contacto normalmente cerrado en lenguaje Ladder (LD) |
| `10052` | **Flanco ascendente** | `ladder_flanco_ascendente` | `-U` | `-` | 1 veces (1 files) | Detector de flanco ascendente P_TRIG en Ladder |
| `10053` | **Flanco descendente** | `ladder_flanco_descendente` | `-U` | `-` | 1 veces (1 files) | Detector de flanco descendente N_TRIG en Ladder |
| `10060` | **Asignar** | `ladder_bobina_asignar` | `Q1,Q2,Q4,Q3,-Q1` | `-` | 6 veces (3 files) | Bobina de salida normal en Ladder ( ) |
| `10061` | **Set** | `ladder_bobina_set` | `-U` | `-` | 1 veces (1 files) | Bobina de activación enclavada (S) Set en Ladder |
| `10062` | **Reset** | `ladder_bobina_reset` | `-U` | `-` | 1 veces (1 files) | Bobina de desactivación (R) Reset en Ladder |
| `10076` | **First Scan** | `ladder_first_scan` | `FIRST` | `SCAN` | 1 veces (1 files) | Contacto especial de primer ciclo de scan en Ladder |

## GRAFCET (11 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `10100` | **Etapa inicial** | `grafcet_etapa_inicial` | `0` | `-` | 1 veces (1 files) | Etapa inicial doble cuadrado GRAFCET |
| `10101` | **Etapa** | `grafcet_etapa` | `1` | `-` | 8 veces (1 files) | Etapa simple numerada GRAFCET |
| `10102` | **Transición** | `grafcet_transicion` | `1,=1` | `-` | 9 veces (1 files) | Barrera de transición con receptividad asociada |
| `10103` | **Acción** | `grafcet_accion` | `-` | `0-0-0-0-0-0-0` | 2 veces (1 files) | Bloque de acción asociada a etapa |
| `10104` | **Divergencia en "O"** | `grafcet_divergencia_o` | `-` | `-` | 1 veces (1 files) | Divergencia alternativa en OR |
| `10105` | **Convergencia en "O"** | `grafcet_convergencia_o` | `-` | `-` | 1 veces (1 files) | Convergencia alternativa en OR |
| `10106` | **"0"** | `grafcet_enlace_cero` | `-` | `-` | 6 veces (1 files) | Línea de enlace y sincronismo GRAFCET |
| `10107` | **Divergencia en "Y"** | `grafcet_divergencia_y` | `1` | `-` | 1 veces (1 files) | Divergencia simultánea en AND (doble barra) |
| `10108` | **Convergencia en "Y"** | `grafcet_convergencia_y` | `1` | `-` | 1 veces (1 files) | Convergencia simultánea en AND (doble barra) |
| `10111` | **Enlace de entrada / salida** | `grafcet_enlace_io` | `M` | `-` | 1 veces (1 files) | Enlace de salto entre etapas o páginas |
| `10112` | **Macro etapa** | `grafcet_macro_etapa` | `-` | `-` | 1 veces (1 files) | Macroetapa jerárquica encapsulada |

## PLC (16 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `10200` | **Intercambio entradas PC_SIMU** | `intercambio_entradas_pc_simu` | `-` | `-` | 2 veces (2 files) | Tabla de comunicación de entradas para PC_SIMU |
| `10201` | **Intercambio salidas PC_SIMU** | `intercambio_salidas_pc_simu` | `-` | `-` | 2 veces (2 files) | Tabla de comunicación de salidas para PC_SIMU |
| `10202` | **Módulo lógico** | `modulo_logico_logo` | `LOGO` | `-` | 3 veces (3 files) | Relé programable Siemens LOGO! (230RC / 24RC) |
| `10203` | **PLC S7-1200** | `plc_s7_1200` | `PLC` | `-` | 1 veces (1 files) | Autómata programable Siemens SIMATIC S7-1200 (CPU 1214C) |
| `10204` | **Entrada digital PLC** | `entrada_digital_plc` | `I0.0` | `-` | 1 veces (1 files) | Borne de entrada digital individual PLC (%I0.x) |
| `10205` | **Salida digital PLC** | `salida_digital_plc` | `Q0.0` | `-` | 1 veces (1 files) | Borne de salida digital individual PLC (%Q0.x) |
| `10206` | **CPU PLC** | `cpu_plc` | `-CPU` | `-` | 1 veces (1 files) | CPU genérica de autómata programable |
| `10207` | **Alimentación I/O digital PLC** | `alimentacion_io_plc_pos` | `1M` | `-` | 2 veces (1 files) | Borne de alimentación positiva para E/S PLC (1L / +24V) |
| `10208` | **Alimentación I/O digital PLC** | `alimentacion_io_plc_neg` | `1L` | `-` | 1 veces (1 files) | Borne de alimentación común / masa para E/S PLC (1M / 0V) |
| `10209` | **PLC CPU S7-1500** | `plc_s7_1500` | `PLC` | `-` | 1 veces (1 files) | Autómata modular Siemens SIMATIC S7-1500 |
| `10210` | **S7-1500 DI/DO** | `modulo_s7_1500_dido` | `PLC` | `0-0` | 1 veces (1 files) | Módulo de entradas y salidas digitales S7-1500 |
| `10212` | **ET-200** | `et_200` | `PLC` | `0-0` | 2 veces (1 files) | Módulo cabecera de periferia distribuida Siemens ET-200 |
| `10213` | **ET-200 8DI** | `et_200_8di` | `PLC` | `0-0` | 1 veces (1 files) | Módulo de 8 entradas digitales para ET-200 |
| `10214` | **LOGO 4DI/4DO** | `logo_4di_4do` | `LOGO` | `9-5` | 1 veces (1 files) | Módulo de expansión para Siemens LOGO! 4DI / 4DO |
| `10215` | **S7-1200 8DI/8DO** | `s7_1200_8di_8do` | `PLC` | `2-2` | 1 veces (1 files) | Módulo de ampliación Siemens SM 1223 (8DI / 8DO) |
| `10220` | **Arduino uno** | `arduino_uno` | `ARDUINO_UNO` | `-` | 1 veces (1 files) | Placa microcontroladora Arduino UNO |

## Neumatica (16 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `1050` | **Actuador simple efecto** | `actuador_simple_efecto` | `-R` | `1-2` | 1 veces (1 files) | Cilindro neumático de simple efecto con retorno por muelle |
| `1051` | **Actuador doble efecto** | `actuador_doble_efecto` | `-R` | `1-3-5-2-4-6` | 1 veces (1 files) | Cilindro neumático de doble efecto |
| `1052` | **Actuador sin vástago** | `actuador_sin_vastago` | `-T` | `1-4-7-2-5-8-3-6-9` | 1 veces (1 files) | Cilindro neumático lineal sin vástago |
| `1053` | **Actuador sin vástago magnético** | `actuador_sin_vastago_mag` | `-G` | `1-3-5-2-4-6-PE` | 1 veces (1 files) | Cilindro sin vástago de arrastre magnético |
| `1054` | **Pinza simple efecto** | `pinza_simple_efecto` | `-G` | `L1-N-PE-U-V-W-PE` | 1 veces (1 files) | Pinza neumática de agarre simple efecto |
| `1055` | **Pinza doble efecto** | `pinza_doble_efecto` | `-G` | `L1-L2-L3-PE-U-V-W-PE` | 1 veces (1 files) | Pinza neumática de agarre doble efecto |
| `1056` | **Ventosa** | `ventosa` | `-G` | `RA-RC-I1-I2-I3-I4-+` | 1 veces (1 files) | Ventosa de vacío con eyector |
| `1057` | **Motor neumático** | `motor_neumatico` | `-G` | `L1-N-PE-M1-M2` | 1 veces (1 files) | Motor neumático unidireccional |
| `1058` | **Motor neumático reversible** | `motor_neumatico_rev` | `-G` | `L1-N-PE-M1-M2-F1-F2` | 1 veces (1 files) | Motor neumático bidireccional |
| `1059` | **Válvula estranguladora** | `valvula_estranguladora` | `-G` | `L1-L2-L3-PE-M1-M2` | 1 veces (1 files) | Válvula reguladora de caudal con antirretorno |
| `1060` | **Válvula escape rápido** | `valvula_escape_rapido` | `-G` | `L1-L2-L3-PE-M1-M2-F1-F2` | 1 veces (1 files) | Válvula de escape rápido para cilindros |
| `1061` | **Electroválvula distribuidora** | `electrovalvula_distribuidora` | `-G` | `RA-RC-IN-V+-+-AI-0V` | 1 veces (1 files) | Válvula distribuidora 5/2 o 3/2 accionamiento eléctrico |
| `1062` | **Actuador giro** | `actuador_giro` | `-G` | `IN-A1-A2` | 1 veces (1 files) | Actuador rotativo / oscilante neumático |
| `1065` | **Final de carrera neumático** | `final_carrera_neumatico` | `-G` | `I1-I2-I3-I4-Q1-Q2-Q3-Q4` | 1 veces (1 files) | Válvula fin de carrera neumática con palpador |
| `1066` | **Pulsador neumático** | `pulsador_neumatico` | `-G` | `I1-I2-I3- -Q1-Q2-Q3-Q4` | 1 veces (1 files) | Válvula 3/2 accionada por pulsador manual |
| `1067` | **Unidad mantenimiento FRL** | `unidad_mantenimiento` | `-G` | `I1-I2-I3- -Q1-Q2-Q3-Q4` | 1 veces (1 files) | Unidad de mantenimiento de aire comprimido (Filtro, Regulador, Lubricador) |

## Cables (16 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `4000` | **Cable fase** | `cable_fase` | `-` | `-` | 220 veces (9 files) | Conductor de fase (marrón/negro/gris) |
| `4001` | **Cable neutro** | `cable_neutro` | `-` | `-` | 133 veces (14 files) | Conductor de neutro (azul claro) |
| `4002` | **Cable protección** | `cable_proteccion` | `-` | `-` | 1 veces (1 files) | Conductor de protección y tierra (verde-amarillo) |
| `4003` | **Cable positivo** | `cable_positivo` | `-` | `-` | 1 veces (1 files) | Conductor de CC positivo (rojo) |
| `4004` | **Cable negativo** | `cable_negativo` | `-` | `-` | 1 veces (1 files) | Conductor de CC negativo (azul oscuro / negro) |
| `4009` | **Conexión** | `cable_conexion` | `-` | `-` | 63 veces (8 files) | Conductor auxiliar o de interconexión general |
| `4010` | **Manguera** | `manguera` | `-` | `-` | 14 veces (5 files) | Manguera multiconductora |
| `4011` | **Cable color** | `cable_gris` | `-X` | `-` | 1 veces (1 files) | Conductor color especial gris |
| `4012` | **Cable color** | `cable_blanco` | `-X` | `-` | 1 veces (1 files) | Conductor color especial blanco |
| `4013` | **Espedor 2** | `cable_espesor_2` | `-X` | `-` | 1 veces (1 files) | Cable de sección reforzada calibre 2 |
| `4014` | **Espedor 3** | `cable_espesor_3` | `-X` | `-` | 1 veces (1 files) | Cable de sección reforzada calibre 3 |
| `4015` | **Espedor 4** | `cable_espesor_4` | `-X` | `-` | 1 veces (1 files) | Cable de sección reforzada calibre 4 |
| `4016` | **Cable color** | `cable_violeta` | `-X` | `-` | 1 veces (1 files) | Conductor de señalización violeta |
| `4017` | **Cable color** | `cable_color_custom` | `-X` | `-` | 1 veces (1 files) | Conductor de control especial |
| `4018` | **Conexión** | `punto_conexion` | `-` | `-` | 340 veces (10 files) | Punto de empalme o derivación de conductores |
| `4019` | **Cable III** | `manguera_trifasica` | `-` | `-` | 12 veces (5 files) | Trazado simultáneo de 3 conductores trifásicos |

## Conexiones (1 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `0` | **Punto de conexión / Conexión eléctrica** | `nodo_conexion` | `$$$,-A-,192.128.000.001,PLC,L+-1-L--1-1` | `-` | 1202 veces (18 files) | Punto de unión/nodo entre conductores |

## 2D_3D (16 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `1076` | **Rele temporizado zócalo** | `rele_temporizado_zocalo` | `-K` | `-` | 1 veces (1 files) | Relé temporizado enchufable sobre base octal/undecal |
| `6015` | **Disyuntor** | `disyuntor_2d_3d` | `-Q` | `1-3-5-2-4-6` | 2 veces (2 files) | Disyuntor de potencia en formato vista 2D/3D |
| `6016` | **Relé térmico** | `rele_termico_2d_3d` | `-F` | `1-3-5-2-4-6` | 2 veces (2 files) | Relé térmico en formato vista 2D/3D |
| `6017` | **Interruptor automático** | `automatico_2d_3d` | `-F` | `N-1-3-5-2-4-6` | 2 veces (2 files) | Interruptor automático magnetotérmico vista 2D/3D |
| `6018` | **Interruptor diferencial** | `diferencial_2d_3d` | `-F` | `N-1-3-5-2-4-6` | 2 veces (2 files) | Interruptor diferencial vista 2D/3D |
| `6019` | **Interruptor** | `interruptor_2d_3d` | `-S` | `N-1-3-5-2-4-6` | 1 veces (1 files) | Interruptor modular vista 2D/3D |
| `6020` | **Seccionador** | `seccionador_2d_3d` | `-S` | `N-1-3-5-2-4-6` | 2 veces (2 files) | Seccionador vista 2D/3D |
| `7016` | **Rele zócalo** | `rele_zocalo_2d_3d` | `-KA` | `13-14-0-1-9-1-5` | 2 veces (2 files) | Base relé enchufable en vista 2D/3D |
| `7018` | **Contactor** | `contactor_2d_3d` | `-KM` | `A1-A2-1-2-3-4` | 2 veces (2 files) | Contactor de potencia en vista 2D/3D |
| `7019` | **Contactos auxiliares** | `contactos_auxiliares_2d_3d` | `-KM` | `-` | 2 veces (2 files) | Bloque contactos auxiliares frontal en 2D/3D |
| `7020` | **Contactos auxiliares ON delay** | `contactos_aux_on_delay_2d_3d` | `-KM` | `0-1-9-1-5` | 1 veces (1 files) | Cámara temporizada neumática ON delay 2D/3D |
| `7021` | **Contactos auxiliares OFF delay** | `contactos_aux_off_delay_2d_3d` | `-KM` | `0-1-9-1-5` | 1 veces (1 files) | Cámara temporizada neumática OFF delay 2D/3D |
| `8100` | **Pulsador** | `pulsador_2d_3d` | `-S` | `.1-.3-.2-.4` | 1 veces (1 files) | Pulsador de cuadro eléctrico en vista 2D/3D |
| `8101` | **Piloto** | `piloto_2d_3d` | `-H` | `X1-X2` | 1 veces (1 files) | Piloto de señalización luminoso en vista 2D/3D |
| `8102` | **Diodo LED** | `diodo_led_2d_3d` | `-H` | `13-14-13-14-11-12-13-14` | 1 veces (1 files) | Diodo LED indicador en vista 2D/3D |
| `8103` | **Borna** | `borna_2d_3d` | `-H` | `-` | 1 veces (1 files) | Borna de paso / conexión en vista 2D/3D |

## Formato (1 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `20000` | **Cajetín** | `cajetin_rotulacion` | `XXX` | `-` | 18 veces (18 files) | Formato de lámina y cuadro de rotulación de plano normalizado |

## Virtual_2D (79 componentes)

| Keycode (CAD ID) | Nombre Original CADe SIMU | Subtipo Interno | Tag Típico | Terminales / Pins | Uso en Ejemplos | Descripción |
|---|---|---|---|---|---|---|
| `1` | **Componente Virtual / Bitmap 1** | `objeto_virtual_1` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_1) |
| `2` | **Componente Virtual / Bitmap 2** | `objeto_virtual_2` | `-` | `-` | 7 veces (6 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_2) |
| `3` | **Componente Virtual / Bitmap 3** | `objeto_virtual_3` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_3) |
| `4` | **Componente Virtual / Bitmap 4** | `objeto_virtual_4` | `$$$` | `-` | 4 veces (4 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_4) |
| `5` | **Componente Virtual / Bitmap 5** | `objeto_virtual_5` | `$$$` | `-` | 5 veces (5 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_5) |
| `6` | **Componente Virtual / Bitmap 6** | `objeto_virtual_6` | `-` | `-` | 3 veces (3 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_6) |
| `7` | **Componente Virtual / Bitmap 7** | `objeto_virtual_7` | `-` | `-` | 8 veces (5 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_7) |
| `8` | **Componente Virtual / Bitmap 8** | `objeto_virtual_8` | `-` | ` 0- 0- 0- 0- 0- 0- 0- 0` | 11 veces (7 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_8) |
| `9` | **Componente Virtual / Bitmap 9** | `objeto_virtual_9` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_9) |
| `10` | **Componente Virtual / Bitmap 10** | `objeto_virtual_10` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_10) |
| `11` | **Componente Virtual / Bitmap 11** | `objeto_virtual_11` | `-` | `-` | 4 veces (4 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_11) |
| `12` | **Componente Virtual / Bitmap 12** | `objeto_virtual_12` | `-` | `-` | 3 veces (3 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_12) |
| `13` | **Componente Virtual / Bitmap 13** | `objeto_virtual_13` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_13) |
| `14` | **Componente Virtual / Bitmap 14** | `objeto_virtual_14` | `-` | `-` | 4 veces (4 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_14) |
| `15` | **Componente Virtual / Bitmap 15** | `objeto_virtual_15` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_15) |
| `16` | **Componente Virtual / Bitmap 16** | `objeto_virtual_16` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_16) |
| `17` | **Componente Virtual / Bitmap 17** | `objeto_virtual_17` | `-` | `-` | 6 veces (4 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_17) |
| `18` | **Componente Virtual / Bitmap 18** | `objeto_virtual_18` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_18) |
| `19` | **Componente Virtual / Bitmap 19** | `objeto_virtual_19` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_19) |
| `20` | **Componente Virtual / Bitmap 20** | `objeto_virtual_20` | `-` | `-` | 6 veces (3 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_20) |
| `21` | **Componente Virtual / Bitmap 21** | `objeto_virtual_21` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_21) |
| `22` | **Componente Virtual / Bitmap 22** | `objeto_virtual_22` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_22) |
| `23` | **Componente Virtual / Bitmap 23** | `objeto_virtual_23` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_23) |
| `24` | **Componente Virtual / Bitmap 24** | `objeto_virtual_24` | `-` | `-` | 6 veces (4 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_24) |
| `25` | **Componente Virtual / Bitmap 25** | `objeto_virtual_25` | `-` | `-` | 3 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_25) |
| `26` | **Componente Virtual / Bitmap 26** | `objeto_virtual_26` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_26) |
| `27` | **Componente Virtual / Bitmap 27** | `objeto_virtual_27` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_27) |
| `28` | **Componente Virtual / Bitmap 28** | `objeto_virtual_28` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_28) |
| `30` | **Componente Virtual / Bitmap 30** | `objeto_virtual_30` | `192.128.000.001` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_30) |
| `31` | **Componente Virtual / Bitmap 31** | `objeto_virtual_31` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_31) |
| `32` | **Componente Virtual / Bitmap 32** | `objeto_virtual_32` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_32) |
| `34` | **Componente Virtual / Bitmap 34** | `objeto_virtual_34` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_34) |
| `35` | **Componente Virtual / Bitmap 35** | `objeto_virtual_35` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_35) |
| `38` | **Componente Virtual / Bitmap 38** | `objeto_virtual_38` | `-` | `-` | 3 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_38) |
| `39` | **Componente Virtual / Bitmap 39** | `objeto_virtual_39` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_39) |
| `41` | **Componente Virtual / Bitmap 41** | `objeto_virtual_41` | `-` | `-` | 3 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_41) |
| `42` | **Componente Virtual / Bitmap 42** | `objeto_virtual_42` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_42) |
| `44` | **Componente Virtual / Bitmap 44** | `objeto_virtual_44` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_44) |
| `45` | **Componente Virtual / Bitmap 45** | `objeto_virtual_45` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_45) |
| `46` | **Componente Virtual / Bitmap 46** | `objeto_virtual_46` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_46) |
| `47` | **Componente Virtual / Bitmap 47** | `objeto_virtual_47` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_47) |
| `48` | **Componente Virtual / Bitmap 48** | `objeto_virtual_48` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_48) |
| `50` | **Componente Virtual / Bitmap 50** | `objeto_virtual_50` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_50) |
| `51` | **Componente Virtual / Bitmap 51** | `objeto_virtual_51` | `-` | `-` | 2 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_51) |
| `52` | **Componente Virtual / Bitmap 52** | `objeto_virtual_52` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_52) |
| `53` | **Componente Virtual / Bitmap 53** | `objeto_virtual_53` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_53) |
| `54` | **Componente Virtual / Bitmap 54** | `objeto_virtual_54` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_54) |
| `55` | **Componente Virtual / Bitmap 55** | `objeto_virtual_55` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_55) |
| `58` | **Componente Virtual / Bitmap 58** | `objeto_virtual_58` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_58) |
| `59` | **Componente Virtual / Bitmap 59** | `objeto_virtual_59` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_59) |
| `61` | **Componente Virtual / Bitmap 61** | `objeto_virtual_61` | `-` | `-` | 3 veces (2 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_61) |
| `62` | **Componente Virtual / Bitmap 62** | `objeto_virtual_62` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_62) |
| `64` | **Componente Virtual / Bitmap 64** | `objeto_virtual_64` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_64) |
| `67` | **Componente Virtual / Bitmap 67** | `objeto_virtual_67` | `-` | `-` | 2 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_67) |
| `69` | **Componente Virtual / Bitmap 69** | `objeto_virtual_69` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_69) |
| `70` | **Componente Virtual / Bitmap 70** | `objeto_virtual_70` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_70) |
| `71` | **Componente Virtual / Bitmap 71** | `objeto_virtual_71` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_71) |
| `77` | **Componente Virtual / Bitmap 77** | `objeto_virtual_77` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_77) |
| `80` | **Componente Virtual / Bitmap 80** | `objeto_virtual_80` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_80) |
| `92` | **Componente Virtual / Bitmap 92** | `objeto_virtual_92` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_92) |
| `105` | **Componente Virtual / Bitmap 105** | `objeto_virtual_105` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_105) |
| `167` | **Componente Virtual / Bitmap 167** | `objeto_virtual_167` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_167) |
| `168` | **Componente Virtual / Bitmap 168** | `objeto_virtual_168` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_168) |
| `170` | **Componente Virtual / Bitmap 170** | `objeto_virtual_170` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_170) |
| `273` | **Componente Virtual / Bitmap 273** | `objeto_virtual_273` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_273) |
| `275` | **Componente Virtual / Bitmap 275** | `objeto_virtual_275` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_275) |
| `277` | **Componente Virtual / Bitmap 277** | `objeto_virtual_277` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_277) |
| `281` | **Componente Virtual / Bitmap 281** | `objeto_virtual_281` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_281) |
| `287` | **Componente Virtual / Bitmap 287** | `objeto_virtual_287` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_287) |
| `293` | **Componente Virtual / Bitmap 293** | `objeto_virtual_293` | `-` | `-` | 1 veces (1 files) | Elemento gráfico / interactivo de laboratorio virtual (bitmap_293) |
| `10500` | **Actuador lineal virtual** | `actuador_lineal_v1` | `-A` | `50-50--a0--a1--a0--a1--A+` | 1 veces (1 files) | Actuador o cilindro lineal en simulación virtual |
| `10501` | **Actuador lineal virtual** | `actuador_lineal_v2` | `-A` | `50-50--a0--a1--a0--a1--A+` | 1 veces (1 files) | Actuador lineal con finales de carrera a0/a1 |
| `10502` | **Actuador lineal virtual** | `actuador_lineal_v3` | `-A` | `50-50--a0--a1--a0--a1--A+` | 1 veces (1 files) | Actuador lineal de doble vástago virtual |
| `10503` | **Actuador lineal virtual** | `actuador_lineal_v4` | `-A` | `50-50--a0--a1--a0--a1--A+` | 1 veces (1 files) | Cilindro neumático simulado virtual |
| `10504` | **Cinta transportadora virtual** | `cinta_transportadora_v1` | `-A` | `50-50--a0--a1--a0--a1--A+` | 1 veces (1 files) | Cinta de transporte con motor reversible |
| `10505` | **Cinta transportadora virtual** | `cinta_transportadora_v2` | `-A` | `50-50--a0--a1--a0--a1--A+` | 1 veces (1 files) | Cinta de transporte con sensores de presencia |
| `10507` | **Válvula virtual** | `valvula_cilindro_virtual` | `-V` | `-v-V+` | 1 veces (1 files) | Válvula de control para maqueta virtual |
| `10508` | **Motor maqueta virtual** | `motor_virtual_1` | `-M` | `50--M+` | 1 veces (1 files) | Motor de accionamiento maqueta |
| `10509` | **Motor maqueta virtual** | `motor_virtual_2` | `-M` | `50-50--MD` | 1 veces (1 files) | Motor con encoder para simulación |

