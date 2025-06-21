import re
import json
import asyncio
import discord
from urllib.parse import urlparse

class AhoCorasickTree:
    
    def __init__(self, words):
        self.build_tree(words)
        self.build_links()
    
    class Node(dict):
        def __init__(self):
            self.word = None
            self.link = None
        
        def iter_links(self):
            current = self
            while current is not current.link:
                yield current
                current = current.link
    
    def iter_nodes(self):
        def inner(tree, path):
            yield path, tree
            for key, node in tree.items():
                yield from inner(node, path + (key,))
        yield from inner(self.tree, ())
    
    def build_tree(self, words):
        self.tree = self.Node()
        for word in words:
            current = self.tree
            for char in word:
                if char not in current:
                    current[char] = self.Node()
                current = current[char]
            current.word = word
    
    def find_node(self, string):
        current = self.tree
        for char in string:
            if char not in current: return None
            current = current[char]
        return current
    
    def build_links(self):
        for path, node in self.iter_nodes():
            for i in range(1, len(path)):
                node.link = self.find_node(path[i:])
                if node.link is not None: break
            else:
                node.link = self.tree
    
    def iter_matches(self, string):
        current = self.tree
        for char in string:
            while char not in current:
                if current is self.tree: break
                current = current.link
            else:
                current = current[char]
                for node in current.iter_links():
                    if node.word: yield node.word

with open("spoilers.json", "r") as f:
    spoilers = json.load(f)

def getwords(string):
    return tuple(re.findall(r"[\w']+", string))

def flatten(text):
    text = text.lower()
    text = re.sub(r"\|\|.+?\|\|", "", text)
    text = re.sub(r":\S+?:", "", text) # emojis
    return text

spoiler_words = [getwords(s) for s in spoilers["text"]]
search_tree = AhoCorasickTree(spoiler_words)

def has_img_spoiler(attachments):
    images = [a for a in attachments if a.content_type.startswith("image/")]
    if all(img.filename.startswith("SPOILER") for img in images): return False
    return True

def has_url_spoiler(text):
    text = text.lower()
    text = re.sub(r"\|\|.+?\|\|", "", text)
    return urlparse(flatten(text)).hostname in spoilers["domains"]

def has_text_spoilers(text):
    words = getwords(flatten(text))
    return bool(next(search_tree.iter_matches(words), False))

def find_text_spoilers(text):
    words = getwords(flatten(text))
    matches = search_tree.iter_matches(words)
    matches = (" ".join(m) for m in matches)
    return sorted(set(matches))

async def handle_spoilers(message):
    text = message.content
    
    if has_img_spoiler(message.attachments):
        delay = 10
        bot_message = await message.reply(
            f"Your message will be deleted in {delay} seconds because it contains an unspoilered image"
            f"\nType `?tag imgspoilers` for instructions on how to spoiler tag images."
        )
        await asyncio.gather(message.delete(delay=delay), bot_message.delete(delay=delay))
        return
    
    if has_text_spoilers(text):
        delay = 15
        found = find_text_spoilers(text)
        bot_message = await message.reply(
            f"Spoilers Detected: ||{', '.join(found)}||"
            f"\nPlease spoiler tag all HK content by adding vertical bars \\||like this\\|| -> ||like this||"
            f"\nEdit your message within {delay} seconds or it will be deleted."
        )
    
    elif has_url_spoiler(text):
        delay = 15
        bot_message = await message.reply(
            f"Untagged URL detected"
            f"\nPlease spoiler tag URLs by adding vertical bars \\||like this\\|| -> ||like this||"
            f"\nEdit your message within {delay} seconds or it will be deleted."
        )
    
    else:
        return
    
    edited_at = None
    while delay > 0:
        await asyncio.sleep(1)
        delay -= 1
        if message.edited_at == edited_at: continue
        edited_at = message.edited_at
        text = message.content
        if not has_url_spoiler(text) and not has_text_spoilers(text):
            await bot_message.delete()
            return
    
    try:
        await asyncio.gather(message.delete(), bot_message.delete())
    except discord.errors.NotFound:
        pass
