from bs4 import BeautifulSoup
from app.database.database import Car
import re

def get_values_car_page(soup:BeautifulSoup, car:Car, link):
    #decided to use self generated id, database conflict on link
    #car.id = parse_car_id(link)
    car.url = link
    car.title = parse_title(soup)
    car.price_usd = parse_price_usd(soup)
    car.odometer = parse_odometer(soup)
    car.username = parse_username(soup)
    #TODO open phone number using javasript button call. BeautifulSoup isn't that beautiful after all. 
    #TODO Need "Selenium" for dynamic interaction 
    car.phone_number = parse_hidden_number(soup)
    car.image_url = parse_image_url(soup)
    car.images_count = parse_photoes_count(soup)
    [car.car_number, car.car_vin] = parse_car_number_vin(soup)
    #car.datetime_found = datetime.utcnow() 

def parse_car_id(link: str) -> int:
    match = re.search(r'_(\d+)\.html', link)
    if match:
        return int(match.group(1))
    
    parts = link.split('_')
    if parts:
        potential_id = "".join(filter(str.isdigit, parts[-1]))
        return int(potential_id)
    
    return 0

def parse_hidden_number(soup:BeautifulSoup, id="sellerInfo")->int:
    container = soup.find("div", id=id)
    if(container):
        phone_button = container.find("button", class_="size-large conversion")
        if(phone_button):
            raw_text = phone_button.get_text()
            # This keeps only digits (0-9)
            clean_number_txt = "".join(filter(str.isdigit, raw_text))
            if(clean_number_txt):
                return int(clean_number_txt)
    return 0

def parse_car_number_vin(soup:BeautifulSoup, id = "badges"):
    container = soup.find("div", id=id)
    if(container):
        text = container.get_text()
        # Pattern explanation:
        # ([A-Z]{2}\s\d{4}\s[A-Z]{2}) -> Finds 2 letters, space, 4 digits, space, 2 letters (Plate)
        # ([A-Z0-9]{17}) -> Finds the next 17 characters (VIN)
        pattern = r"([A-Z]{2}\s\d{4}\s[A-Z]{2})([A-Z0-9]{17})"
        match = re.search(pattern, text)
        if match:
            car_number = match.group(1)
            car_vin = match.group(2)
            return [car_number, car_vin]
        
    return ["", ""]


def parse_image_url(soup:BeautifulSoup, id = "photoSlider")->str:
    #TODO get multiple link to database. Create one-to-many 
    #PS. TT said I should use one link only
    container = soup.find("div", id=id)
    if(container):
        img_tags = container.find_all("img")
        img_links = []
        for tag in img_tags:
            src = tag.get("data-src")
            #TODO remove temp line
            return src
            img_links.append(src)
        #TODO return full list of links
        if(len(img_links)>0):
            return img_links[0]
    
    return ""


def parse_photoes_count(soup:BeautifulSoup, class_ = "common-badge alpha medium") -> int:
    photo_count_obj = soup.find("span", class_=class_)
    if(photo_count_obj):
        photo_text = photo_count_obj.get_text()
        numbers = re.findall(r'\d+', photo_text)
        return int(numbers[1]) if len(numbers) > 1 else 0
    
    return 0
    
def parse_title(soup:BeautifulSoup, id = "sideTitleTitle") -> str:
    car_title_obj = soup.find("div", id=id)
    if(car_title_obj):
        return car_title_obj.get_text()
    return ""

def parse_username(soup:BeautifulSoup, id = "sellerInfoUserName") -> str:
    car_username_obj = soup.find("div", id=id)
    if(car_username_obj):
        car_username_text = car_username_obj.get_text()
        return car_username_text
    return ""

def parse_price_usd(soup:BeautifulSoup, id="sidePrice") -> int:
    car_price_obj = soup.find("div", id=id)
    if(car_price_obj):
        car_price_text = car_price_obj.get_text()
        if('$' in car_price_text):
            txt = car_price_text.split('$')[0]
            #remove space from txt
            clean_price = re.sub(r'\s', '', txt)
            if(clean_price):
                car_price_usd = int(clean_price)
                return car_price_usd
    return 0

def parse_odometer(soup:BeautifulSoup, id="basicInfoTableMainInfo0")->int:
    odometer_obj = soup.find("div", id=id)
    if(odometer_obj):
        odometer_text = odometer_obj.get_text()
        digits_only = re.sub(r'\D', '', odometer_text)
        if digits_only:
            value = int(digits_only)

            # 2. Check if the string mentions "thousands"
            if "тис" in odometer_text.lower():
                return value * 1000

            return value
    return 0
