#TODO run this with unittest test runner or some other repo
import chunking
import retrieval
import unittest
class TestCase(unittest.TestCase):
    def test_table_chunking(self):
        '''
        Tests the ability of the process_document method to correctly chunk a table-based document into small chunks as 
        python dictionaries each containing few rows (in this case 1 row). Note:
        1. the title is added as a comment to the chunk
        2. the table is "flattened" with each row as a dictionary with the headers as keys
        '''
        #...........................................................................
        document = {
            'title': 'countries and captials',
            'table': {
                'headers' : ['country','capital'],
                'rows': [
                    ['india','new delhi'],
                    ['japan','tokyo'],
                    ['china','beijing'],
                ]
            }
        }
        expected_chunks = ['# Table for: countries and captials\n[{"country":"india","capital":"new delhi"}]',
                          '# Table for: countries and captials\n[{"country":"japan","capital":"tokyo"}]',
                           '# Table for: countries and captials\n[{"country":"china","capital":"beijing"}]',
                          ]
        #...........................................................................
        chunks = chunking.process_document(document)
        chunks = [c['text'] for c in chunks]

        assert len(chunks) == len(expected_chunks)
        expected_chunks = [eval(c) for c in expected_chunks]
        for c in chunks:
            assert eval(c) in expected_chunks, c
        pass


    def test_code_chunking(self):
        '''
        Tests the ability of the process_document method to correctly chunk a code based document. Note:
        1. the title is added as a comment to the chunk
        '''
        #...........................................................................
        document = {
            'title': 'list comprehension in python',
            'code_block': 'l=[i**2 for i in range(10)]'
        }
        expected_chunks = ['# Code Block for: list comprehension in python\n\nl=[i**2 for i in range(10)]']
        #...........................................................................
        chunks = chunking.process_document(document)
        chunks = [c['text'] for c in chunks]

        assert len(chunks) == len(expected_chunks)
        for c_expected,c_found in zip(expected_chunks,chunks):
            assert c_expected == c_found, c_found
    def test_hierarchical_chunking(self):
        '''
        Tests the ability of the process_document method to correctly chunk a hierarchical document, containing sections, subsections etc. Note:
        1. All titles encountered in traversing to the content are accumulated. These are added as a Title line to the top of the chunk
        '''

        #...........................................................................
        document = {
            'title': 'High School Mathematics',
            'sections':[{
                'title': 'Integral Calculus',
                'subsections' : [{
                    'title' : 'Fundamental Theorem of Algebra',
                    'content' : 'We now describe...'
                }]
            }]

        }
        expected_chunks = ['Title: High School Mathematics,Integral Calculus,Fundamental Theorem of Algebra\n\nWe now describe...']
        #...........................................................................
        chunks = chunking.process_document(document)
        chunks = [c['text'] for c in chunks]

        assert len(chunks) == len(expected_chunks)
        for c_expected,c_found in zip(expected_chunks,chunks):
            assert c_expected == c_found, c_found
    def test_retrieve_chunks(self):

        '''
        Tests the retrieve_chunks function's ability to retrieve relevant chunks
        '''
        chunks = [
            {'text': 'The sky is blue', 'metadata': {'raw_content': 'The sky is blue and clear'}},
            {'text': 'The grass is green', 'metadata': {'raw_content': 'The grass is green and lush'}},
            {'text': 'Roses are red', 'metadata': {'raw_content': 'Roses are red, violets are blue'}}
        ] 
        top_k = 1
        expected_chunks = ['The sky is blue']
        query = 'What color is the sky?'
        result = retrieval.retrieve_chunks(query, chunks, top_k=top_k)
        
        self.assertEqual(len(result), top_k)
        self.assertEqual(result[0]['chunk'], expected_chunks[0])
        #self.assertEqual(result[1]['chunk'], expected_chunks[1])
if __name__ == '__main__':
    unittest.main()

