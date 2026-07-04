from dotenv import load_dotenv

load_dotenv()

from journal import create_app  # noqa: E402

app = create_app()
