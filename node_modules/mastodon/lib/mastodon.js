//
//  Mastodon API Wrapper
//
var assert = require('assert');
var Promise = require('bluebird');
var request = require('request');
var util = require('util');
var helpers = require('./helpers');
var STATUS_CODES_TO_ABORT_ON = require('./settings').STATUS_CODES_TO_ABORT_ON;

var DEFAULT_REST_ROOT = 'https://mastodon.social/api/v1/';

var required_for_user_auth = [
  'access_token',
];

//
//  Mastodon
//
var Mastodon = function (config) {
  if (!(this instanceof Mastodon)) {
    return new Mastodon(config);
  }

  var self = this
  var credentials = {
    access_token : config.access_token
  }

  this.apiUrl = config.api_url || DEFAULT_REST_ROOT;

  this._validateConfigOrThrow(config);
  this.config = config;
  this._mastodon_time_minus_local_time_ms = 0;
}

Mastodon.prototype.get = function (path, params, callback) {
  return this.request('GET', path, params, callback)
}

Mastodon.prototype.post = function (path, params, callback) {
  return this.request('POST', path, params, callback)
}

Mastodon.prototype.patch = function (path, params, callback) {
  return this.request('PATCH', path, params, callback)
}

Mastodon.prototype.delete = function (path, params, callback) {
  return this.request('DELETE', path, params, callback)
}

Mastodon.prototype.request = function (method, path, params, callback) {
  var self = this;
  assert(method == 'GET' || method == 'POST' || method == 'PATCH' || method == 'DELETE');
  // if no `params` is specified but a callback is, use default params
  if (typeof params === 'function') {
    callback = params
    params = {}
  }

  return new Promise(function (resolve, reject) {
    var _returnErrorToUser = function (err) {
      if (callback && typeof callback === 'function') {
        callback(err, null, null);
      }
      reject(err);
    }

    self._buildReqOpts(method, path, params, function (err, reqOpts) {
      if (err) {
        _returnErrorToUser(err);
        return
      }

      var mastoOptions = (params && params.masto_options) || {};

      process.nextTick(function () {
        // ensure all HTTP i/o occurs after the user has a chance to bind their event handlers
        self._doRestApiRequest(reqOpts, mastoOptions, method, function (err, parsedBody, resp) {
          self._updateClockOffsetFromResponse(resp);

          if (self.config.trusted_cert_fingerprints) {
            if (!resp.socket.authorized) {
              // The peer certificate was not signed by one of the authorized CA's.
              var authErrMsg = resp.socket.authorizationError.toString();
              var err = helpers.makeMastodonError('The peer certificate was not signed; ' + authErrMsg);
              _returnErrorToUser(err);
              return;
            }
            var fingerprint = resp.socket.getPeerCertificate().fingerprint;
            var trustedFingerprints = self.config.trusted_cert_fingerprints;
            if (trustedFingerprints.indexOf(fingerprint) === -1) {
              var errMsg = util.format('Certificate untrusted. Trusted fingerprints are: %s. Got fingerprint: %s.',
                                       trustedFingerprints.join(','), fingerprint);
              var err = new Error(errMsg);
              _returnErrorToUser(err);
              return;
            }
          }

          if (callback && typeof callback === 'function') {
            callback(err, parsedBody, resp);
          }

          resolve({ data: parsedBody, resp: resp });
          return;
        })
      })
    });
  });
}

Mastodon.prototype._updateClockOffsetFromResponse = function (resp) {
  var self = this;
  if (resp && resp.headers && resp.headers.date &&
      new Date(resp.headers.date).toString() !== 'Invalid Date'
  ) {
    var mastodonTimeMs = new Date(resp.headers.date).getTime()
    self._mastodon_time_minus_local_time_ms = mastodonTimeMs - Date.now();
  }
}

/**
 * Builds and returns an options object ready to pass to `request()`
 * @param  {String}   method      "GET", "POST", or "DELETE"
 * @param  {String}   path        REST API resource uri (eg. "statuses/destroy/:id")
 * @param  {Object}   params      user's params object
 * @returns {Undefined}
 *
 * Calls `callback` with Error, Object where Object is an options object ready to pass to `request()`.
 *
 * Returns error raised (if any) by `helpers.moveParamsIntoPath()`
 */
Mastodon.prototype._buildReqOpts = function (method, path, params, callback) {
  var self = this
  if (!params) {
    params = {}
  }
  var finalParams = params;
  delete finalParams.masto_options

  // the options object passed to `request` used to perform the HTTP request
  var reqOpts = {
    headers: {
      'Accept': '*/*',
      'User-Agent': 'node-mastodon-client',
      'Authorization': 'Bearer ' + self.config.access_token
    },
    gzip: true,
    encoding: null,
  }

  if (typeof self.config.timeout_ms !== 'undefined') {
    reqOpts.timeout = self.config.timeout_ms;
  }

  try {
    // finalize the `path` value by building it using user-supplied params
    path = helpers.moveParamsIntoPath(finalParams, path)
  } catch (e) {
    callback(e, null, null)
    return
  }

  if (path.match(/^https?:\/\//i)) {
    // This is a full url request
    reqOpts.url = path
  } else {
    // This is a REST API request.
    reqOpts.url = this.apiUrl + path;
  }

  if (finalParams.file) {
    // If we're sending a file
    reqOpts.headers['Content-type'] = 'multipart/form-data';
    reqOpts.formData = finalParams;
  } else {
    // Non-file-upload params should be url-encoded
    if (Object.keys(finalParams).length > 0) {
      reqOpts.url += this.formEncodeParams(finalParams);
    }
  }

  callback(null, reqOpts);
  return;
}

/**
 * Make HTTP request to Mastodon REST API.
 * @param  {Object}   reqOpts     options object passed to `request()`
 * @param  {Object}   mastoOptions
 * @param  {String}   method      "GET", "POST", or "DELETE"
 * @param  {Function} callback    user's callback
 * @return {Undefined}
 */
Mastodon.prototype._doRestApiRequest = function (reqOpts, mastoOptions, method, callback) {
  var request_method = request[method.toLowerCase()];
  var req = request_method(reqOpts);

  var body = '';
  var response = null;

  var onRequestComplete = function () {
    if (body !== '') {
      try {
        body = JSON.parse(body)
      } catch (jsonDecodeError) {
        // there was no transport-level error, but a JSON object could not be decoded from the request body
        // surface this to the caller
        var err = helpers.makeMastodonError('JSON decode error: Mastodon HTTP response body was not valid JSON')
        err.statusCode = response ? response.statusCode: null;
        err.allErrors.concat({error: jsonDecodeError.toString()})
        callback(err, body, response);
        return
      }
    }

    if (typeof body === 'object' && (body.error || body.errors)) {
      // we got a Mastodon API-level error response
      // place the errors in the HTTP response body into the Error object and pass control to caller
      var err = helpers.makeMastodonError('Mastodon API Error')
      err.statusCode = response ? response.statusCode: null;
      helpers.attachBodyInfoToError(err, body);
      callback(err, body, response);
      return
    }

    // success case - no errors in HTTP response body
    callback(err, body, response)
  }

  req.on('response', function (res) {
    response = res
    // read data from `request` object which contains the decompressed HTTP response body,
    // `response` is the unmodified http.IncomingMessage object which may contain compressed data
    req.on('data', function (chunk) {
      body += chunk.toString('utf8')
    })
    // we're done reading the response
    req.on('end', function () {
      onRequestComplete()
    })
  })

  req.on('error', function (err) {
    // transport-level error occurred - likely a socket error
    if (mastoOptions.retry &&
        STATUS_CODES_TO_ABORT_ON.indexOf(err.statusCode) !== -1
    ) {
      // retry the request since retries were specified and we got a status code we should retry on
      self.request(method, path, params, callback);
      return;
    } else {
      // pass the transport-level error to the caller
      err.statusCode = null
      err.code = null
      err.allErrors = [];
      helpers.attachBodyInfoToError(err, body)
      callback(err, body, response);
      return;
    }
  })
}

Mastodon.prototype.formEncodeParams = function (params, noQuestionMark) {
  var encoded = '';
  for (var key in params) {
    var value = params[key];
    if (encoded === '') {
      if (!noQuestionMark) {
        encoded = '?';
      }
    } else {
      encoded += '&';
    }

    if (Array.isArray(value)) {
      value.forEach(function(v) {
        encoded += encodeURIComponent(key) + '[]=' + encodeURIComponent(v) + '&';
      });
    } else {
      encoded += encodeURIComponent(key) + '=' + encodeURIComponent(value);
    }
  }

  return (encoded);
}

Mastodon.prototype.setAuth = function (auth) {
  var self = this
  var configKeys = [
    'access_token'
  ];

  // update config
  configKeys.forEach(function (k) {
    if (auth[k]) {
      self.config[k] = auth[k]
    }
  })
  this._validateConfigOrThrow(self.config);
}

Mastodon.prototype.getAuth = function () {
  return this.config
}

//
// Check that the required auth credentials are present in `config`.
// @param {Object}  config  Object containing credentials for REST API auth
//
Mastodon.prototype._validateConfigOrThrow = function (config) {
  //check config for proper format
  if (typeof config !== 'object') {
    throw new TypeError('config must be object, got ' + typeof config)
  }

  if (typeof config.timeout_ms !== 'undefined' && isNaN(Number(config.timeout_ms))) {
    throw new TypeError('Mastodon config `timeout_ms` must be a Number. Got: ' + config.timeout_ms + '.');
  }

  var auth_type = 'user auth'
  var required_keys = required_for_user_auth

  required_keys.forEach(function (req_key) {
    if (!config[req_key]) {
      var err_msg = util.format('Mastodon config must include `%s` when using %s.', req_key, auth_type)
      throw new Error(err_msg)
    }
  })
}

module.exports = Mastodon
