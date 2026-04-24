import os
import argparse
from .utils.data_loader import load_matches
from .utils.metrics import factory_metrics, osb_metrics
from .utils.prompt_builder import build_factory_prompt, build_osb_prompt
from .utils.llm_client import generate_report

def main():
    parser = argparse.ArgumentParser(description="Endüstriyel Simbiyoz Raporlayıcı")
    parser.add_argument("--excel", required=True, help="Excel dosyasının yolu")
    parser.add_argument("--previous_excel", required=False, help="Geçen ayın Excel dosyasının yolu")
    parser.add_argument("--persona", required=True, choices=['factory', 'osb'], help="Rapor hedefi: 'factory' veya 'osb'")
    parser.add_argument("--factory_id", required=False, help="Eğer persona 'factory' ise factory_id gereklidir")
    parser.add_argument("--model", default="llama3.1", help="Kullanılacak Ollama modeli (varsayılan: llama3.1)")
    
    args = parser.parse_args()
    
    if args.persona == 'factory' and not args.factory_id:
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

    if args.persona == 'factory':
        print(f"Fabrika ({args.factory_id}) için metrikler hesaplanıyor...")
        metrics = factory_metrics(df, args.factory_id, previous_df)
        prompt = build_factory_prompt(metrics)
        report_name = f"factory_report_{args.factory_id}.txt"
    else:
        print("OSB için metrikler hesaplanıyor...")
        metrics = osb_metrics(df, previous_df)
        prompt = build_osb_prompt(metrics)
        report_name = "osb_report.txt"
        
    print(f"LLM çağrısı yapılıyor: model = {args.model}")
    report_content = generate_report(prompt, model=args.model)
    
    # Reports klasörünü oluştur
    base_dir = os.path.dirname(os.path.abspath(__file__))
    reports_dir = os.path.join(base_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    output_path = os.path.join(reports_dir, report_name)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
        
    print(f"Rapor oluşturuldu ve kaydedildi: {output_path}")

if __name__ == "__main__":
    main()
