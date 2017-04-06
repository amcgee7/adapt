__author__ = 'seanfitz'

CLIENT_ENTITY_NAME = 'Client'


def is_entity(tag, entity_name):
    """This doesn't look like it is used any where?
    """
    for entity in tag.get('entities'):
        for v, t in entity.get('data'):
            if t.lower() == entity_name.lower():
                return True
    return False


def find_first_tag(tags, entity_type, after_index=-1):
    """Searches tags for entity type after given index

    Parameters
    ----------
    tags: [] - a list of tags with entity types to be compaired too entity_type
    entity_type: str - This is he entity type to be looking for in tags
    after_index: int - the start token must be greaterthan this.

    Returns
    -------
    ( tag, v, confidence )
    tag: str - is the tag that matched
    v: str - ? the word that matched?
    confidence: double - is a mesure of accuacy.  1 is full confidence and 0 is none.
    """
    for tag in tags:
        for entity in tag.get('entities'):
            for v, t in entity.get('data'):
                if t.lower() == entity_type.lower() and tag.get('start_token', 0) > after_index:
                    return tag, v, entity.get('confidence')
    return None, None, None


def find_next_tag(tags, end_index=0):
    """This doesn't look like it's used anywhere?"""
    for tag in tags:
        if tag.get('start_token') > end_index:
            return tag
    return None


def choose_1_from_each(lists):
    """Takes a list of lists and returns a list of lists with one item
    from each list.  This new list should be the length of each list multiplied
    by the others.  18 for an list with lists of 3, 2 and 3.  Also the lenght
    of each sub list should be same as the length of lists passed in.

    Properties
    ----------
    lists: [[]] - A list of lists

    Returns
    -------
    [[]] - returns a list of lists constructions of one item from each
    list in lists.
    """
    if len(lists) == 0:
        yield []
    else:
        for el in lists[0]:
            for next_list in choose_1_from_each(lists[1:]):
                yield [el] + next_list


def resolve_one_of(tags, at_least_one):
    """This searches tags for Entites in at_least_one and returns any match

    Parameters
    ----------
    tags: [] - List of tags with Entities to search for Entities
    at_least_one: [] - List of Entities to find in tags

    Returns
    -------
    {} - returns None if no match is found but returns any match as an object
    """
    if len(tags) < len(at_least_one):
        return None
    for possible_resolution in choose_1_from_each(at_least_one):
        resolution = {}
        pr = possible_resolution[:]
        for entity_type in pr:
            last_end_index = -1
            if entity_type in resolution:
                last_end_index = resolution.get[entity_type][-1].get('end_token')
            tag, value, c = find_first_tag(tags, entity_type, after_index=last_end_index)
            if not tag:
                break
            else:
                if entity_type not in resolution:
                    resolution[entity_type] = []
                resolution[entity_type].append(tag)
        if len(resolution) == len(possible_resolution):
            return resolution
    return None


class Intent(object):
    def __init__(self, name, requires, at_least_one, optional):
        """Create Intent object

        Parameters
        ----------
        name - str - Name for Intent
        requires - Entities that are required
        at_least_one - One of these Entities are required
        optional - Optional Entities used by the intent
        """
        self.name = name
        self.requires = requires
        self.at_least_one = at_least_one
        self.optional = optional

    def validate(self, tags, confidence):
        """Using this method removes tags from the result of validate_with_tags

        Returns
        -------
        intent - class intent - Resuts from validate_with_tags
        """
        intent, tags = self.validate_with_tags(tags, confidence)
        return intent

    def entities(self):
        """Used to get the Entities the intent is looking for.

        Returns
        -------
        [] - A list of Entities the intent is looking for.  This should
        never be empty but still could be.
        """
        entities = []
        thelist = self.requires + self.at_least_one + self.optional
        for entity in thelist:
            if type(entity) is tuple:
                entityx, name = entity
                entities.append(entityx)
            else:
                entities.append(entity)
        return entities

    def validate_with_tags(self, tags, confidence):
        """Validate weather tags has required entites for this intent to fire

        Parameters
        ----------
        tags - Tags and Entities used for validation
        confidence - ?

        Returns
        -------
        (intent, tags) - Returns intent and tags used by the intent on
        falure to meat required entities then returns intent with confidence
        of 0.0 and an empty list for tags.
        """
        result = {'intent_type': self.name}
        intent_confidence = 0.0
        local_tags = tags[:]
        used_tags = []

        for require_type, attribute_name in self.requires:
            required_tag, canonical_form, confidence = find_first_tag(local_tags, require_type)
            if not required_tag:
                result['confidence'] = 0.0
                return result, []

            result[attribute_name] = canonical_form
            if required_tag in local_tags:
                local_tags.remove(required_tag)
            used_tags.append(required_tag)
            # TODO: use confidence based on edit distance and context
            intent_confidence += confidence

        if len(self.at_least_one) > 0:
            best_resolution = resolve_one_of(tags, self.at_least_one)
            if not best_resolution:
                result['confidence'] = 0.0
                return result, []
            else:
                for key in best_resolution:
                    result[key] = best_resolution[key][0].get('key') # TODO: at least one must support aliases
                    intent_confidence += 1.0
                used_tags.append(best_resolution)
                if best_resolution in local_tags:
                    local_tags.remove(best_resolution)

        for optional_type, attribute_name in self.optional:
            optional_tag, canonical_form, conf = find_first_tag(local_tags, optional_type)
            if not optional_tag or attribute_name in result:
                continue
            result[attribute_name] = canonical_form
            if optional_tag in local_tags:
                local_tags.remove(optional_tag)
            used_tags.append(optional_tag)
            intent_confidence += 1.0

        total_confidence = intent_confidence / len(tags) * confidence

        target_client, canonical_form, confidence = find_first_tag(local_tags, CLIENT_ENTITY_NAME)

        result['target'] = target_client.get('key') if target_client else None
        result['confidence'] = total_confidence

        return result, used_tags


class IntentBuilder(object):
    """
    IntentBuilder, used to construct intent parsers.
    """
    def __init__(self, intent_name):
        """
        Constructor

        :param intent_name: the name of the intents that this parser parses/validates

        :return: an instance of IntentBuilder
        """
        self.at_least_one = []
        self.requires = []
        self.optional = []
        self.name = intent_name

    def one_of(self, *args):
        """
        The intent parser should require one of the provided entity types to validate this clause.

        :param args: *args notation list of entity names

        :return: self
        """
        self.at_least_one.append(args)
        return self

    def require(self, entity_type, attribute_name=None):
        """
        The intent parser should require an entity of the provided type.

        :param entity_type: string, an entity type

        :param attribute_name: string, the name of the attribute on the parsed intent. Defaults to match entity_type.

        :return: self
        """
        if not attribute_name:
            attribute_name = entity_type
        self.requires += [(entity_type, attribute_name)]
        return self

    def optionally(self, entity_type, attribute_name=None):
        """
        Parsed intents from this parser can optionally include an entity of the provided type.

        :param entity_type: string, an entity type

        :param attribute_name: string, the name of the attribute on the parsed intent. Defaults to match entity_type.

        :return: self
        """
        if not attribute_name:
            attribute_name = entity_type
        self.optional += [(entity_type, attribute_name)]
        return self

    def build(self):
        """
        Constructs an intent from the builder's specifications.

        :return: an Intent instance.
        """
        return Intent(self.name, self.requires, self.at_least_one, self.optional)


""" For testing locally """
if __name__ == "__main__":
    import pprint
    from adapt.parser import Parser
    from adapt.entity_tagger import EntityTagger
    from adapt.tools.text.tokenizer import EnglishTokenizer
    from adapt.tools.text.trie import Trie

    class IntentTest:

        def __init__(self):
            self.trie = Trie()
            self.tokenizer = EnglishTokenizer()
            self.regex_entities = []
            self.tagger = EntityTagger(self.trie, self.tokenizer, regex_entities=self.regex_entities)
            self.trie.insert("play", ("play", "PlayVerb"))
            self.trie.insert("play", ("play", "Command"))
            self.trie.insert("the big bang theory", ("the big bang theory", "Television Show"))
            self.trie.insert("all that", ("all that", "Television Show"))
            self.trie.insert("all that", ("all that", "Radio Station"))
            self.trie.insert("the big", ("the big", "Not a Thing"))
            self.trie.insert("barenaked ladies", ("barenaked ladies", "Radio Station"))
            self.trie.insert("show", ("show", "Command"))
            self.trie.insert("what", ("what", "Question"))
            self.parser = Parser(self.tokenizer, self.tagger)
            self.intent = IntentBuilder("Test Intent").require("PlayVerb").one_of("Television Show","Radio Station").build()

        def teststring(self,stringA):
            results = []
            for result in self.parser.parse(stringA):
                result_intent = self.intent.validate(result.get('tags'), result.get('confidence'))
                results.append(result_intent)
            return results

    test = IntentTest()
    #print "Result %s " % test.teststring("show the big bang theory")
    #print "Result %s " % test.teststring("play barenaked ladies")
    print("Result %s " % test.teststring("play all that"))
    #print "Result %s " % test.teststring("play pair")

