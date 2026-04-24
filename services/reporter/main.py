import argparse
from pathlib import Path

from .utils.data_loader import load_matches
from .utils.metrics import factory_metrics, osb_metrics
from .utils.prompt_builder import build_factory_prompt, build_osb_prompt
from .utils.llm_client import generate_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Endüstriyel Simbiyoz Raporlayıcı")
    parser.add_argument("--excel", required=True, help="Excel dosyasının yolu")
    parser.add_argument("--previous_excel", help="Geçen ayın Excel dosyasının yolu")
    parser.add_argument(
        "--persona",
        required=True,
        choices=["factory", "osb"],
        help="Rapor hedefi: 'factory' veya 'osb'",
    )
    parser.add_argument("--factory_id", help="Eğer persona 'factory' ise factory_id gereklidir")
    parser.add_argument("--model", default="llama3.1", help="Kullanılacak Ollama modeli (varsayılan: llama3.1)")
    return parser


def _report_spec(args, df, previous_df):
    if args.persona == "factory":
        print(f"Fabrika ({args.factory_id}) için metrikler hesaplanıyor...")
        return (
            build_factory_prompt(factory_metrics(df, args.factory_id, previous_df)),
            f"factory_report_{args.factory_id}.txt",
        )
    print("OSB için metrikler hesaplanıyor...")
    return build_osb_prompt(osb_metrics(df, previous_df)), "osb_report.txt"


def main():
    args = _build_parser().parse_args()

    if args.persona == "factory" and not args.factory_id:
        print("Hata: persona 'factory' seçildiğinde --factory_id parametresi de verilmelidir.")
        return

    print(f"Güncel veri yükleniyor: {args.excel}")
    df = load_matches(args.excel)
    if df is None:
        return

    previous_df = None
    if args.previous_excel:
        print(f"Geçmiş veri yükleniyor: {args.previous_excel}")
        previous_df = load_matches(args.previous_excel)
        if previous_df is None:
            print("Uyarı: geçmiş Excel yüklenemedi. Karşılaştırma yapılamayacak.")

    prompt, report_name = _report_spec(args, df, previous_df)
    print(f"LLM çağrısı yapılıyor: model = {args.model}")
    report_content = generate_report(prompt, model=args.model)

    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    output_path = reports_dir / report_name
    output_path.write_text(report_content, encoding="utf-8")

    print(f"Rapor oluşturuldu ve kaydedildi: {output_path}")


if __name__ == "__main__":
    main()
