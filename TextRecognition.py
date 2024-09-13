
import pytesseract

form_tuple = ('Форма № 057/у-04','№ 057/у-04',"057/у-04")
def image_to_text(array):
    img_array = array
    recognized_texts = ''
    text = pytesseract.image_to_string(img_array, lang='rus')
    if any(word in text for word in form_tuple):
        return True
    else:
        return False 
        
