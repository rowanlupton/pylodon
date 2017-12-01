from ..utils import get_content
from ..errors import DiscoveryError

import contextlib
import html.parser


def discover(url, timeout=None):
    """Discover the hub url and topic url of a given url. Firstly, by inspecting
    the page's headers, secondarily by inspecting the content for link tags.

    timeout determines how long to wait for the url to load. It defaults to 3.

    """
    resp = get_content({'REQUEST_TIMEOUT': timeout}, url)

    parser = LinkParser()
    parser.hub_url = (resp.links.get('hub') or {}).get('url')
    parser.topic_url = (resp.links.get('self') or {}).get('url')
    try:
        parser.updated()
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            parser.feed(chunk)
        parser.close()
    except Finished:
        return {'hub_url': parser.hub_url, 'topic_url': parser.topic_url}

    raise DiscoveryError("Could not find hub url in topic page")


class LinkParser(html.parser.HTMLParser):
    def updated(self):
        if self.hub_url and self.topic_url:
            raise Finished()

    def handle_starttag(self, tag, attrs_list):
        if tag == 'link' or tag.endswith(':link'):
            # .endswith() risks false positives, but real XML parsing is too
            # much trouble to be worth it
            attrs = dict(attrs_list)
            with contextlib.suppress(KeyError):
                rel = attrs['rel']
                if not self.hub_url and rel == 'hub':
                    self.hub_url = attrs['href']
                    self.updated()
                if not self.topic_url and rel == 'self':
                    self.topic_url = attrs['href']
                    self.updated()


class Finished(Exception):
    pass
