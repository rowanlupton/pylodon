from app import mongo

from OpenSSL import crypto

def generate_keys():
	key = crypto.PKey()
	cert = crypto.X509()

	key.generate_key(crypto.TYPE_RSA, 512)

	public_key = crypto.dump_publickey(crypto.FILETYPE_PEM, key)
	private_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
	
	return public_key, private_key

def sign_item(data, id):
	public_key = mongo.db.users.find({'id': id})['public_key']

	key = crypto.load_publickey(crypto.FILETYPE_PEM, public_key)

	return crypto.sign(key, data, b"sha256")

def verify_signature(item, id):
	pass
