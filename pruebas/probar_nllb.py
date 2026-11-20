from app.services.motor_nllb import MotorNLLB

motor = MotorNLLB()

resultado = motor.traducir(
    texto="Hola, como estas?",
    idioma_origen="es",
    idioma_destino="en",
)

print("Traduccion:")
print(resultado)