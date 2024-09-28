from flask import Flask, request, render_template, send_file
import pandas as pd
import xml.etree.ElementTree as ET
import os
import uuid

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'ファイルがアップロードされていません。', 400

    file = request.files['file']
    if file.filename == '':
        return 'ファイル名が無効です。', 400

    print(f'アップロードされたファイルのMIMEタイプ: {file.content_type}')  # デバッグ用

    # XMLファイルのMIMEタイプをチェック
    if file.content_type in ['application/xml', 'text/xml']:
        # 一時ファイルの保存
        file_id = str(uuid.uuid4())
        xml_file_path = f'uploads/{file_id}.xml'
        os.makedirs('uploads', exist_ok=True)
        file.save(xml_file_path)

        # XMLファイルの解析とCSV出力
        csv_file_path = parse_xml_to_csv(xml_file_path)

        return send_file(csv_file_path, as_attachment=True)

    else:
        return '無効なファイルタイプです。XMLファイルをアップロードしてください。', 400

def parse_xml_to_csv(xml_file_path):
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except (FileNotFoundError, ET.ParseError) as e:
        return f'XMLファイルの解析に失敗しました: {str(e)}', 400

    calculations = {}
    column_map = {}

    # datasourcesの取得
    for datasource in root.iter('datasource'):
        datasource_caption = datasource.get('caption')
        for column in datasource.iter('column'):
            caption = column.get('caption')
            name = column.get('name')
            calculation = column.find('calculation')
            param_domain_type = column.get('param-domain-type')

            # Calculation_名とキャプションのマッピングを作成
            if calculation is not None:
                column_map[name] = caption

            if param_domain_type is not None:
                label = 'パラメータ'
                aliases = column.find('aliases')
                formula = 'N/A'
                if aliases is not None:
                    alias_pairs = {alias.get('key').replace('.', ''): alias.get('value') for alias in aliases.findall('alias')}
                    formula = ', '.join([f"{key}: '{value}'" for key, value in alias_pairs.items()])
            elif calculation is not None:
                label = '計算フィールド'
                formula = calculation.get('formula', 'N/A')
            else:
                continue

            if caption not in calculations:
                calculations[caption] = {
                    'Formula': formula,
                    'Data Type': column.get('datatype'),
                    'Label': label,
                    'Datasource': datasource_caption
                }

    # 計算式の中のCalculation_をキャプションに置き換え
    for caption, info in calculations.items():
        if info['Label'] == '計算フィールド':
            formula = info['Formula']
            for name, col_caption in column_map.items():
                if col_caption:
                    formula = formula.replace(name, col_caption)
            info['Formula'] = formula

    # DataFrameを作成
    df_calculations = pd.DataFrame.from_dict(calculations, orient='index').reset_index()
    df_calculations.columns = ['Caption', 'Formula', 'Data Type', 'Label', 'Datasource']

    # CSVファイルとして保存
    csv_file_path = f'uploads/{uuid.uuid4()}.csv'
    df_calculations.to_csv(csv_file_path, index=False, encoding='utf-8-sig')

    return csv_file_path

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)  # アップロード用ディレクトリを事前に作成
    app.run(debug=True)
