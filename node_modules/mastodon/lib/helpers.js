var querystring = require('querystring');
var request = require('request');

/**
 * For each `/:param` fragment in path, move the value in params
 * at that key to path. If the key is not found in params, throw.
 * Modifies both params and path values.
 *
 * @param  {Objet} params  Object used to build path.
 * @param  {String} path   String to transform.
 * @return {Undefined}
 *
 */
exports.moveParamsIntoPath = function (params, path) {
  var rgxParam = /\/:(\w+)/g
  var missingParamErr = null

  path = path.replace(rgxParam, function (hit) {
    var paramName = hit.slice(2)
    var suppliedVal = params[paramName]
    if (!suppliedVal) {
      throw new Error('Mastodon: Params object is missing a required parameter for this request: `'+paramName+'`')
    }
    var retVal = '/' + suppliedVal
    delete params[paramName]
    return retVal
  })
  return path
}

/**
 * When Mastodon returns a response that looks like an error response,
 * use this function to attach the error info in the response body to `err`.
 *
 * @param  {Error} err   Error instance to which body info will be attached
 * @param  {Object} body JSON object that is the deserialized HTTP response body received from Mastodon
 * @return {Undefined}
 */
exports.attachBodyInfoToError = function (err, body) {
  err.mastodonReply = body;
  if (!body) {
    return
  }
  if (body.error) {
    // the body itself is an error object
    err.message = body.error
    err.allErrors = err.allErrors.concat([body])
  } else if (body.errors && body.errors.length) {
    // body contains multiple error objects
    err.message = body.errors[0].message;
    err.code = body.errors[0].code;
    err.allErrors = err.allErrors.concat(body.errors)
  }
}

exports.makeMastodonError = function (message) {
  var err = new Error()
  if (message) {
    err.message = message
  }
  err.code = null
  err.allErrors = []
  err.mastodonReply = null
  return err
}
