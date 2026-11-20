import torch

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.constants.idiomas_nllb import IDIOMAS_NLLB


MODELO_NLLB = "facebook/nllb-200-distilled-600M"


class MotorNLLB:

    def __init__(self):
        self.dispositivo = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print(f"Cargando NLLB-200 en: {self.dispositivo}")

        self.tokenizador = AutoTokenizer.from_pretrained(
            MODELO_NLLB
        )

        self.modelo = AutoModelForSeq2SeqLM.from_pretrained(
            MODELO_NLLB
        )

        self.modelo.to(self.dispositivo)
        self.modelo.eval()

        print("NLLB-200 cargado correctamente.")

    def traducir(
        self,
        texto: str,
        idioma_origen: str,
        idioma_destino: str,
    ) -> str:

        codigo_origen = IDIOMAS_NLLB.get(idioma_origen)
        codigo_destino = IDIOMAS_NLLB.get(idioma_destino)

        if not codigo_origen:
            raise ValueError(
                f"Idioma de origen no soportado: {idioma_origen}"
            )

        if not codigo_destino:
            raise ValueError(
                f"Idioma de destino no soportado: {idioma_destino}"
            )

        self.tokenizador.src_lang = codigo_origen

        entradas = self.tokenizador(
            texto,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )

        entradas = {
            clave: valor.to(self.dispositivo)
            for clave, valor in entradas.items()
        }

        id_idioma_destino = self.tokenizador.convert_tokens_to_ids(
            codigo_destino
        )

        with torch.no_grad():

            tokens_traducidos = self.modelo.generate(
                **entradas,
                forced_bos_token_id=id_idioma_destino,
                max_length=512,
            )

        traduccion = self.tokenizador.batch_decode(
            tokens_traducidos,
            skip_special_tokens=True,
        )[0]

        return traduccion