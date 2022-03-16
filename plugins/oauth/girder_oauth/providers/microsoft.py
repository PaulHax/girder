# -*- coding: utf-8 -*-
import urllib.parse

from msal import ConfidentialClientApplication

from girder.exceptions import RestException
from girder.models.setting import Setting

from .base import ProviderBase
from ..settings import PluginSettings


class Microsoft(ProviderBase):
    _MSR_TENANT = 'common'  # TODO: allow custom tenant ID from plugin GUI
    _AUTHORITY = f'https://login.microsoftonline.com/{_MSR_TENANT}'
    _AUTH_SCOPES = ['User.Read']
    _API_USER_URL = 'https://graph.microsoft.com/v1.0/me'

    def getClientIdSetting(self):
        return Setting().get(PluginSettings.MICROSOFT_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(PluginSettings.MICROSOFT_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(PluginSettings.MICROSOFT_CLIENT_ID)
        if not clientId:
            raise Exception('No Microsoft client ID setting is present.')

        clientSecret = Setting().get(PluginSettings.MICROSOFT_CLIENT_SECRET)
        if not clientSecret:
            raise Exception('No Microsoft client secret setting is present.')

        app = ConfidentialClientApplication(
            client_id=clientId,
            client_credential=clientSecret,
            authority=cls._AUTHORITY,
        )
        # The default response type is 'code', so we don't need to pass it
        url = app.get_authorization_request_url(
            scopes=cls._AUTH_SCOPES,
            state=state,
        )
        return url

    def getToken(self, code):
        app = ConfidentialClientApplication(
            client_id=self.clientId,
            client_credential=self.clientSecret,
            authority=self._AUTHORITY,
        )
        result = app.acquire_token_by_authorization_code(
            code,
            self._AUTH_SCOPES,
        )
        if 'access_token' not in result:
            strings = result['error'], result['error_description']
            raise Exception('Error "%s" acquiring access token for client: %s' % strings)
        return result

    def getUser(self, token):
        headers = {
            'Authorization': 'Bearer %s' % token['access_token'],
            'Accept': 'application/json'
        }

        # Get user's OAuth2 ID, email, and name
        resp = self._getJson(method='GET', url=self._API_USER_URL, headers=headers)

        oauthId = resp.get('id')
        if not oauthId:
            raise RestException('Microsoft did not return user ID.', code=502)

        email = resp.get('mail')
        if not email:
            raise RestException(
                'This Microsoft user has no registered email address.', code=502)

        # Get user's name
        firstName = resp.get('givenName', '')
        lastName = resp.get('surname', '')

        user = self._createOrReuseUser(oauthId, email, firstName, lastName)
        return user
