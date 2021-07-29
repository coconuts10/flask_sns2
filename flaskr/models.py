# models.py
from flaskr import db, login_manager
from flask_bcrypt import generate_password_hash,check_password_hash
from flask_login import UserMixin, current_user
from sqlalchemy.orm import aliased  #参照先を複数テーブルで紐づける。
from sqlalchemy import and_, or_, desc   #and_複数条件を指定して、複数の条件すべてが満たしている場合0uter_joinで紐づける。
                                    #or_複数条件を指定して、1つでも満たしている場合、outer join紐づける

from datetime import datetime, timedelta

#パスワードをするときに便利な機能
from uuid import uuid4

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class User(UserMixin, db.Model):

    __tablename__ =  'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(
        db.String(128),
        default=generate_password_hash('snsflaskapp')
    )

    picture_path = db.Column(db.Text)
    #有効か無効かのフラグ
    is_active = db.Column(db.Boolean, unique=False, default=False)

    #DBにいつ更新されたデータか分かるように付ける
    create_at =db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    #emailとusernameを設定したコンストラクタを設定する
    def __init__(self, username, email):
        self.username = username    #self.usernameはclass自体に定義されている変数を示す。
                                    #dbのテーブル情報を取得すときによく使う記述。
        self.email = email

    @classmethod    #pythonのメソッドはインスタンスにしないと呼び出せないが、@classmethodだと、
                    #クラスをインポートした段階で利用できる。
    def select_user_by_email(cls, email):   #clsはクラスメソッド内でクラス自身を参照できるようにする為の引数。
                                            #通常のインスタンスメソッドはselfでインスタンス自信を参照するようにしている。
                                            #ここのclsはusersテーブルの中身全体を参照している
        return cls.query.filter_by(email=email).first() #SQL検索結果で先頭1件を返す

    def validate_password(self, password):
        return check_password_hash(self.password, password)

    def create_new_user(self):
        db.session.add(self)

    @classmethod
    def select_user_by_id(cls, id):
        return cls.query.get(id)

    def save_new_password(self, new_password):
        self.password = generate_password_hash(new_password)
        self.is_active = True

    #UserConnectと紐づける。outer joinを使う。
    #→UserConnectに紐づけられなかった場合にもNullとして取得できる。
    @classmethod
    def search_by_name(cls, username, page=1):  #複雑だが、一回の実行で多くの情報を取得したほうが性能がいい。
        user_connect1 = aliased(UserConnect) #from_user_id：検索相手のID、to_user_id：ログインユーザーのIDでUcserConnectに紐づける。
        user_connect2 = aliased(UserConnect) #to_user_id：検索相手のID、from_user_id：ログインユーザーのIDでUcserConnectに紐づける。
        return cls.query.filter(
            cls.username.like(f'%{username}%'), #like句であり全権一致検索で検索を行う。
                                               #usernameで入力した値が含まれるものだけを抽出する。
            cls.id != int(current_user.get_id()),
            cls.is_active == True
        ).outerjoin(
            user_connect1,
            and_(
                user_connect1.from_user_id == cls.id,   #cls.idは検索したユーザー情報のユーザーID
                user_connect1.to_user_id == current_user.get_id()
            )
        ).outerjoin(
            user_connect2,
            and_(
                user_connect2.from_user_id == current_user.get_id(),
                user_connect2.to_user_id == cls.id
            )
        ).with_entities(        #取り出すカラムを指定する。
            cls.id, cls.username,cls.picture_path,
            user_connect1.status.label("joined_status_to_from"),    #joined_status_to_fromは取り出した検索結果のラベル名を示す。
            user_connect2.status.label("joined_status_from_to")     #joined_status_from_toは取り出した検索結果のラベル名を示す。
        ).order_by(cls.username).paginate(page, 50, False)           #結果をリストで返す。paginateでSQLalcemyの機能で、ページ処理ができる。                                     #このようにラベルを持たせることで、user_search.htmlとのやり取りをスムーズに行うことができる。

    @classmethod
    def select_friends(cls):
        return cls.query.join(  #usersテーブルとuserconnectテーブルで結合する。
            UserConnect,
            or_(
                and_(
                    UserConnect.to_user_id == cls.id,
                    UserConnect.from_user_id == current_user.get_id(),
                    UserConnect.status == 2
                ),
                and_(
                    UserConnect.from_user_id == cls.id,
                    UserConnect.to_user_id == current_user.get_id(),
                    UserConnect.status == 2
                )
            )
        ).with_entities(
            cls.id, cls.username, cls.picture_path  #当該関数はclass User(UserMixin, db.Model):配下のものであり、
                                                    #clsによUserクラスの情報を参照できる。すなわち、検索したユーザー情報のusesテーブルの中身が見れる。
        ).all()

    @classmethod
    def select_requested_friends(cls):
        return cls.query.join(
            UserConnect,
            and_(
                UserConnect.from_user_id == cls.id,
                UserConnect.to_user_id == current_user.get_id(),
                UserConnect.status == 1
            )
        ).with_entities(
            cls.id, cls.username, cls.picture_path
        ).all()

    @classmethod
    def select_requesting_friends(cls):
        return cls.query.join(
            UserConnect,
            and_(
                UserConnect.from_user_id == current_user.get_id(),
                UserConnect.to_user_id == cls.id,
                UserConnect.status == 1
            )
        ).with_entities(
            cls.id, cls.username, cls.picture_path
        ).all()


#パスワードリセット時に利用する
class PasswordResetToken(db.Model):

    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(
        db.String(64),
        unique=True,
        index=True,
        default=str(uuid4)
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expire_at = db.Column(db.DateTime, default=datetime.now)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, token, user_id, expire_at):
        self.token = token
        self.user_id = user_id
        self.expire_at = expire_at

    @classmethod
    def publish_token(cls, user):
        #パスワード設定用URLを生成
        token = str(uuid4())
        new_token = cls(
            token,
            user.id,
            #tokenの有効期限
            datetime.now() + timedelta(days=1)
        )
        db.session.add(new_token)
        return token

    @classmethod
    def get_user_id_by_token(cls, token):
       now = datetime.now()
       record = cls.query.filter_by(token=str(token)).filter(cls.expire_at > now).first()
       if record:
           return record.user_id
       else:
           return None

    @classmethod
    def delete_token(cls, token):
        cls.query.filter_by(token=str(token)).delete()

class UserConnect(db.Model):

    __tablename__ = 'user_connects'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    )   #どのユーザーからの友達申請か
    to_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    )   #どのユーザーへの友達申請か
    status = db.Column(db.Integer,  unique=False, default=1)
    #1申請中, 2承認済み
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, from_user_id, to_user_id):   #UserConnectクラスが呼び出されたときにこちらの関数が自動実行される。
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id

    def create_new_connect(self):
        db.session.add(self)

    @classmethod
    def select_by_from_user_id(cls, from_user_id):
        return cls.query.filter_by(
            from_user_id = from_user_id,
            to_user_id = current_user.get_id()
        ).first()

    def update_status(self):
        self.status = 2
        self.update_at = datetime.now()

    @classmethod
    def is_friend(cls, to_user_id): #home.htmlでapp.messageを実行することで、views.pyのmessage関数が呼び出される。
                                    #app.messageでidを引数にしており、これがto_user_idにあたる。
        user = cls.query.filter(
            or_(
                and_(
                    UserConnect.from_user_id == current_user.get_id(),
                    UserConnect.to_user_id == to_user_id,
                    UserConnect.status == 2
                ),
                and_(
                    UserConnect.from_user_id == to_user_id,
                    UserConnect.to_user_id == current_user.get_id(),
                    UserConnect.status == 2
                )
            )
        ).first()
        return True if user else False

class Message(db.Model):

    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    )
    to_user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), index=True
    )
    is_read = db.Column(
        db.Boolean, default=False
    )
    #既読のものを確認したか
    is_checked = db.Column(
        db.Boolean, default=False
    )
    message = db.Column(
        db.Text
    )
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, from_user_id, to_user_id, message):
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.message = message

    def create_message(self):
        db.session.add(self)

    @classmethod
    def get_friend_messages(cls, id1, id2, offset_value=0, limit_value=100):    #limit_valueでvalueを飛ばす数を決める。
                                                                                #offset_valueで飛ばす位置を示す。
        return cls.query.filter(    #自分→相手のメッセージと相手→自分のメッセージの両方を取得する
            or_(
                and_(
                    cls.from_user_id == id1,
                    cls.to_user_id == id2
                ),
                and_(
                    cls.from_user_id == id2,
                    cls.to_user_id == id1
                )
            )                                                #メッセージの表示を順番を並び変える為に使う。
        ).order_by(desc(cls.id)).offset(offset_value).limit(limit_value).all()  #最新の100件を取り出す。（順番は逆になっている。）                             #メッセージが追加された順にIDが割り振られるのでIDで並べる。
        #このようにoffsetとlimit関数を使うことで、性能を向上することができる。

    @classmethod
    def update_is_read_by_ids(cls, ids):
        cls.query.filter(cls.id.in_(ids)).update(   #idの中に、引数のidsが入っている場合にupdateする。
            {'is_read':1},
            synchronize_session='fetch' #fetchはレコードを更新する前にSELECTを実行して更新対象のレコードを取得する。
                                        #evaluateはデフォルト。UPDATE実行時にSQLの抽出条件IN句をチェックす。IN句は現状対応していないのでエラーになる。
        )

    @classmethod
    def update_is_checked_by_ids(cls, ids):
        cls.query.filter(cls.id.in_(ids)).update(  # idの中に、引数のidsが入っている場合にupdateする。
            {'is_checked': 1},
            synchronize_session='fetch'  # fetchはレコードを更新する前にSELECTを実行して更新対象のレコードを取得する。
            # evaluateはデフォルト。UPDATE実行時にSQLの抽出条件IN句をチェックす。IN句は現状対応していないのでエラーになる。
        )

    @classmethod
    def select_not_read_messages(cls, from_user_id, to_user_id):    #相手から自分へのメッセージでまだ読まれていないものを抽出する。
        return cls.query.filter(
            and_(
                cls.from_user_id == from_user_id,
                cls.to_user_id == to_user_id,
                cls.is_read == 0
            )
        ).order_by(cls.id).all()

    @classmethod
    def select_not_checked_messages(cls, from_user_id, to_user_id):
        return cls.query.filter(
            and_(
                cls.from_user_id == from_user_id,
                cls.to_user_id == to_user_id,
                cls.is_read == 1,
                cls.is_checked == 0
            )
        ).order_by(cls.id).all()



