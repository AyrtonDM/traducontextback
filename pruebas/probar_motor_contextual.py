from app.services.motor_contextual import MotorContextual


motor = MotorContextual()


resultado = motor.analizar(
    contexto="financial institution",
    texto="I went to the bank."
)


print(resultado)