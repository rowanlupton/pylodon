from werkzeug.security import check_password_hash, generate_password_hash

class BaseModel(object):
  def __init__(self, id=None):
    self.id = id

  @property
  def id(self):
    return self.id

  @id.setter
  def id(self, value):
    self.id = value


class User(BaseModel):
	# user who will query api
	def __init__(self, id=None, username=None, hashpw=None):
		super(User,self),__init__(id)
		self._username = username
		self._hashpw = hashpw

	@property
	def username(self):
		return self._username

	@property
	def hashpw(self):
		return self._hashpw

  @property
  def authenticated(self):
    return True

  @property
  def anonymous(self):
    return False

  @property
  def active(self):
    return True

  @staticmethod
  def validate_login(password_hash, password):
    return check_password_hash(password_hash, password)

  @staticmethod
  def hash_password(password):
    return generate_password_hash(password, 'pbkdf2:sha256', 8)

class Client(BaseModel):
	# client application

	def __init__(self, id=None, client_id=None, client_type=None):
		super(Client, self).__init__(id)
		self._client_id = client_id
		self._client_type = client_type

	@property
	def client_id(self):
		return self._client_id

	@property
	def client_type(self):
		return self._client_type

	@property
	def allowed_grant_types(self):
		return ['password', 'refresh_token']

	@property
	def default_scopes(self):
		return []

	@property
	def default_redirect_uri(self):
		return '/oauth/callback'



class Token(BaseModel):

	def __init__(self, id=None, client_id=None, username=None, user=None,
                 token_type=None, access_token=None, refresh_token=None,
                 expires=None, scopes=['']):
		super(Token, self).__init__(id)
		self._client_id = client_id
		self._username = username
		self._user = None
		self._token_type = token_type
		self._access_token = access_token
		self._refresh_token = refresh_token
		self._expires = get_expiration_time()
		self._scopes = scopes

	@property
	def client_id(self):
		return self._client_id

	@property
	def username(self):
		return self._user_id

	@property
	def user(self):
		return self._user

	@user.setter
	def user(self, value):
		self._user = value

	@property
	def token_type(self):
		return self._token_type

	@token_type.setter
	def token_type(self, value):
		self._token_type = value

	@property
	def access_token(self):
		return self._access_token

	@access_token.setter
	def access_token(self, value):
		self._access_token = value

	@property
	def refresh_token(self):
		return self._refresh_token

	@refresh_token.setter
	def refresh_token(self, value):
		self._refresh_token = value

	@property
	def expires(self):
		return self._expires.replace(tzinfo=None)

	@expires.setter
	def expires(self, value):
		self._expires = value

	@property
	def scopes(self):
		return self._scopes

	@scopes.setter
	def scopes(self, value):
		self._scopes = value




