class Encoder():
    """
    Technique for padding a string as defined in RFC 2315, section 10.3,
    note #2
    """
    class InvalidBlockSizeError(Exception):
        """Raised for invalid block sizes"""
        pass

    def __init__(self, block_size=16):
        if block_size < 2 or block_size > 255:
            raise PKCS7Encoder.InvalidBlockSizeError('The block size must be ' \
                    'between 2 and 255, inclusive')
        self.block_size = block_size

    def encode(self, text):
        text_length = len(text)
        ''' pad the file up to multiple of self.block_size '''
        amount_to_pad = self.block_size - (text_length % self.block_size)
        ''' still pad one block_size if already a multiple '''
        if amount_to_pad == 0:
            amount_to_pad = self.block_size
        ''' convert the amount_to_pad to character '''
        pad = chr(amount_to_pad)
        return text + pad * amount_to_pad

    def decode(self, text):
        pad = ord(text[-1])
        return text[:-pad]
