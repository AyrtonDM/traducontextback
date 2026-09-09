from app.services.motor_contextual import MotorContextual


motor = MotorContextual()


resultado = motor.analizar(
    contexto="????",
    texto="???????????"
)


print(resultado)