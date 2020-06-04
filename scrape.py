import urllib.request  as urllib2
import urllib
from bs4 import BeautifulSoup
import re
import pandas as pd
from selenium import webdriver
import time
import pymongo

def set_driver(driver_path):
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument('--headless')
    driver = webdriver.Chrome(driver_path, chrome_options=options)
    return driver



def getSongData(url, driver_path):

    driver = set_driver(driver_path)
    driver.get(url)
    time.sleep(2)
    
    # Obtiene el lyric de la canción
    # Extraer página
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')
    
    lyric = None
    lyric = soup.find('div', class_='holder lyric-box')
    trash = lyric.findAll('span')
    for e in trash:
        _ = e.extract()
    trash = lyric.findAll('div')
    for e in trash:
        _ = e.extract()
    lyric = lyric.getText()
    
    # Obtiene todos los comentarios
    
    all_comments = []
    all_responses = []
    
    # all_comments => comentRating, commentType, commentText, commentUserName, commentDate, commentTotAnswers 
    # all_responses => arrays of [ansRating, ansDate, ansAuthor, answerText]
    
    while True:

        #Extraer página
        page_source = driver.page_source

        #Extraer comentarios
        soup = BeautifulSoup(page_source, 'lxml')
        comments = soup.find('ul', class_='comments-list').find_all('li', id=re.compile('^fullcomment-'))

        for comment in comments:

            comentRating = comment.find('div', class_='numb-holder').find('strong').getText()       

            answersObj = comment.find('ul', class_='answers').extract()
            signObj = comment.find('div', class_='sign').extract()
            commentObj = comment.find('div', class_='text')

            #print('commentObj:: ', commentObj)
            commentType = commentObj.find('strong').extract().getText()
            commentText = commentObj.getText()
            commentUserName = signObj.find('a', class_='author')['title']
            commentDate = signObj.find('em').getText()

            arr = answersObj.find_all('div', class_='answer-holder')
            commentTotAns = len(arr)
            commentAnswers = []
            for ans in arr:
                ansRating = ans.find('div', class_='numb-holder').find('strong').getText()
                ansSignObj = ans.find('div', class_='sign').extract()
                ansDate = ansSignObj.find('em').getText()
                ansAuthor = ansSignObj.find('a', class_='author')['title']
                answerText = ans.find('div', class_='text').getText()

                commentAnswers.append([ansRating, ansDate, ansAuthor, answerText])

            all_comments.append([ comentRating, commentType, commentText, commentUserName, commentDate, commentTotAns])
            all_responses.append(commentAnswers)


        # Boton siguiente pagina de comentarios
        siguiente = driver.find_element_by_id('pagination').find_elements_by_tag_name('a')[-1]
        if(siguiente.text != 'next'):
            # Termina la paginación de comentarios
            break
        # Para evitar overlapping de ads con el boton siguiente se hace scroll hasta el final
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        siguiente.click()
        time.sleep(2)

    driver.close()
    return (lyric, all_comments, all_responses)

def scrapeSongs(driver_path, songs_file):
    '''Gaaa'''
    mongo_uri= "mongodb+srv://admin_joel:kumenasaibd2399@noobcluster-fss7a.mongodb.net/test?retryWrites=true&w=majority"
    
    client = pymongo.MongoClient(mongo_uri)
    database = client["data_analysis"]
    songsCol = database["songs"]
    commentsCol = database["comments"]
    
    mainArtists = pd.read_csv(songs_file)
    mainSongs = pd.read_csv('mainSongs.csv')
    mainArtists.columns = ['ID', 'ARTIST', 'ARTIST_SONGS_LINK', 'TOTAL_SONGS']
    mainSongs.columns = ['ID','ARTIST', 'SONG_NAME', 'SONG_LINK', 'LYRIC' ]
    songLinks = mainSongs['SONG_LINK']
    
    i = 0
    for song in mainSongs.iterrows():
        lyric = ''
        comments = []
        responses = []
        
        # try:
        lyric, comments, responses = getSongData(song[1]['SONG_LINK'], driver_path)
        # except:
        #     print('Error in song ', i)
            
        
        # Store song data in mongo
        song = {
            'artist': song[1]['ARTIST'],
            'name':song[1]['SONG_NAME'],
            'link': song[1]['SONG_LINK'],
            'lyric': lyric,
            'totComments': len(comments)
        }
        
        aux = songsCol.insert_one(song)
        song_id = aux.inserted_id

        comments_obj = []

        for comment in comments:
            obj = {
                'songId': song_id,
                'rating': comment[0],
                'type': comment[1],
                'text': comment[2],
                'userName': comment[3],
                'date': comment[4],
                'totalResponses': comment[5],
                'parentId': ''
            }
            comments_obj.append(obj)

        auxComments = commentsCol.insert_many(comments_obj)

        responses_obj = []

        for j in range(len(comments)):
            if comments[j][5] > 0:
                # Tiene respuestas y se almacenan como comentarios hijos
                for response in responses[j]:
                    obj = {
                        'songId': song_id,
                        'rating': response[0],
                        'type': 'RESPONSE',
                        'text': response[3],
                        'userName': response[2],
                        'date': response[1],
                        'totalResponses': 0,
                        'parentId': auxComments.inserted_ids[j]
                    }
                    responses_obj.append(obj)
        
        auxResponses = commentsCol.insert_many(responses_obj)

        print('Song ', i)
        i+=1

if __name__ == "__main__":

    songs_file = 'mainArtists.csv'        

    driver_path= "/Users/joel/Documents/ad/chromedriver"

    scrapeSongs(driver_path, songs_file)
