import glob
import re
from collections import Counter
import numpy as np
from bs4 import BeautifulSoup

class Email:
    def __init__(self,path):
        self.path = path
        self.is_spam = None
        with open(self.path, "r") as file :
            mail = file.read( )
            addr = re.search(r'(.*)[\t| X]+(.*)@(.*)', mail, re.I | re.M)

            self.shipper = addr.group(2) + "@" + addr.group(3)
            self.receiver = "unknown"
            self.date = re.search(r'data:[\t| X]+(.*)', mail, re.I | re.M).group(1)
            self.subject = re.search(r'temat:[\t| X]+(.*)', mail, re.M | re.I).group(1)
            self.content = re.search(r'Treść:[\t| X]+(.*)', mail, re.I | re.M).group(1)
            file.close( )

    def read_mail(self,path):
        self.__init__(path)

    def print_mail(self):
        with open(self.path, "r") as file :
            mail = file.read( )
            print(mail)
            file.close( )

def add_from_xml(path = 'spam/dict.xml'):
    spam_buf = []
    ham_buf = []
    f = open(path, 'r')
    xml = f.read( )
    soup = BeautifulSoup(xml, 'lxml')

    for tag in soup.findAll("word") :
        if tag["type"] == "spam":
            spam_buf.append((tag.text,float(tag["probabilty"])))
        else:
            ham_buf.append((tag.text, float(tag["probabilty"])))
    f.close( )

    return spam_buf, ham_buf

def tokenize(source):
    words = re.split(r'[,?| X]', source)
    while '' in words : words.remove('')
    return words

def calculate_prob(test_path = "spam/example.txt", k_laplace = 0, add_dict = True):
    mails = []
    words_dict = {"spam" : [], "ham" : []}
    labels = []

    for file in glob.glob(r"spam/*[0-9].txt") :
        mail = Email(file)
        mails.append(mail)

        label = re.split(r"[\\ |.X]" , file)[1]
        labels.append(label)
        #print(labels)

        words = tokenize(mail.content)
        subject_words = tokenize(mail.subject)

        words.extend(subject_words)

        if label == 'spam' :
            words_dict["spam"].extend(words)
        else :
            words_dict["ham"].extend(words)

    num_words_spam = len(words_dict["spam"])
    num_words_ham = len(words_dict["ham"])

    count_words_spam = Counter(words_dict["spam"])
    count_words_ham = Counter(words_dict["ham"])

    P_word_spam = [] # P(wordi|SPAM)
    P_word_ham = []

    for item in count_words_spam.items( ) :
        P_word_spam.append((item[0], item[1] / (num_words_spam + k_laplace*2)))

    for item in count_words_ham.items( ) :
        P_word_ham.append((item[0], item[1] / (num_words_ham + k_laplace*2)))

    #Dodawanie slowniak z pliku xml
    if add_dict :
        spam_buf, ham_buf = add_from_xml( )
        P_word_spam.extend(spam_buf)
        P_word_ham.extend(ham_buf)

    count_category = Counter(labels)

    P_spam = (count_category['spam'] + k_laplace) / (len(labels) + k_laplace*2) #P(SPAM)
    P_ham = (count_category['ham']  + k_laplace) / (len(labels) + k_laplace*2)

    #Testowanie pliku example.txt
    test_words = None
    with open(test_path, "r") as test :
        mail = Email(test_path)
        test_words = tokenize(mail.content)
        test_subject_words = tokenize(mail.subject)
        test_words.extend(test_subject_words)

    print(P_word_spam)
    spam_words, P_word_spam = list(zip(*P_word_spam))
    ham_words, P_word_ham = list(zip(*P_word_ham))

    P_message_spam = []
    P_message_ham = []

    similarity_margin = 2   #Zmienna okreslajaca na ile podobne moga byc wyrazy w zbiorze wyrazow
                            #pobranych z plikow, w porownaniu z plikiem testowym example.txt

    for word in test_words :
        found_in_spam = 0
        found_in_ham = 0

        for i in range(similarity_margin) :
            if not found_in_spam :
                for i, spam_word in enumerate(spam_words) :
                    if spam_word.startswith(word) :
                        P_message_spam.append(P_word_spam[i])
                        #print("S " + word + " " + str(P_word_spam[i]))
                        found_in_spam = 1
                        break

            if not found_in_ham :
                for i, ham_word in enumerate(ham_words) :
                    if ham_word.startswith(word) :
                        P_message_ham.append(P_word_ham[i])
                        #print("H " + word + " " + str(P_word_ham[i]))
                        found_in_ham = 1
                        break

            word = word[:-1] #Skracanie slowa z tresci maila,
                             #w celu powiekszenia zakresu mozliwych dopasowan

        if not found_in_spam : P_message_spam.append(0.0001)
        if not found_in_ham : P_message_ham.append(0.0001)

    P_message_spam = np.cumprod(P_message_spam)[-1] #P(message|SPAM)
    P_message_ham = np.cumprod(P_message_ham)[-1]

    P_spam_message = P_message_spam * P_spam / (P_message_spam * P_spam + P_message_ham * P_ham) #P(SPAM|message)
    P_ham_message = P_message_ham * P_ham / (P_message_spam * P_spam + P_message_ham * P_ham)

    print("Prawdopodobienstwo tego że wiadomość jest spamem: " + str(P_spam_message * 100) + " [%]")
    print("Prawdopodobienstwo tego że wiadomość nie jest spamem: " + str(P_ham_message * 100) + " [%]")


if __name__ == '__main__':
    path = "spam/example.txt"
    with open(path, "r") as f:
        print(f.read( ))

    print("Bez wygladzania Laplace'a:")
    calculate_prob(path)
    print("\nZ wygladzaniem Laplace'a")
    calculate_prob(path, k_laplace=2)
