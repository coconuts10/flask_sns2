#__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from flaskr.utils.template_filters import replace_newline

login_manager = LoginManager()
login_manager.login_view = 'app.view'
login_manager.login_message = 'ログインしてください'

basedir = os.path.abspath(os.path.dirname(__name__))
db = SQLAlchemy()   #変数dbにSQLAlchemyのライブラリ情報を入れる
migrate = Migrate()

def create_app():
    app = Flask(__name__)       #appという名前でFLASKのインスタンスを作成。
                                #__name__とは、 Python のプログラムがどこから呼ばれて実行されているかを格納している変数
                                #__name__==__main__の場合、現在のモジュール（ファイル）にて実行されている事を示す。
                                #なぜここで__name__が必要かというと、後々出てくるtemplates(htmlを格納)やstatic(CSSやJSを格納)
                                #の位置をFlaskに知らせるため
    app.config['SECRET_KEY'] = 'mysite' #セキュリティキー。セッションなどで用いられる。乱数が望ましい。
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite') #sqlite:///とはメモリ上のデータを指す
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    from flaskr.views import bp     #flaskrフォルダ配下のviews.pyの中にあるbp変数をインポート
    app.register_blueprint(bp)      #Blueprintをアプリケーションに登録する。
    app.add_template_filter(replace_newline)    #カスタムテンプレートフィルターにreplace_newline登録する。これによりhtmlでjinjaを利用する際にeplace_newlineをテンプレートとして利用できる。
    db.init_app(app)
    migrate.init_app(app, db)       #マイグレーションとはプログラムのコードからデータベースにテーブルを作成・編集すること
    login_manager.init_app(app)
    return app