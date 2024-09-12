import asyncio
import locale
import os
import time
import traceback
import urllib3
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(filename='error.log', format='%(asctime)s | %(message)s', encoding='utf-8')

# Константы:

BOT_TOKEN = '7248211528:AAHJjVPhCxm6_4Uawha1Ie3vl4T58k-9ZzM'  

CHAT_ID = '-1002265212679'  

RSS_FEED_URL = 'https://function.mil.ru/rss_feeds/reference_to_general.htm?contenttype=xml'

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}

# Set the locale to Russian
# locale.setlocale(locale.LC_TIME, 'ru_RU')


async def download_image(url, news_id):
    response = requests.get(url, headers=headers, allow_redirects=True, verify=False)
    image_filename = f"temp_image_{news_id}.jpg"
    with open(image_filename, 'wb') as file:
        file.write(response.content)
    return image_filename


def convert_date(input_date):
    # Define month names in Russian
    month_names = {
        'Jan': 'января',
        'Feb': 'февраля',
        'Mar': 'марта',
        'Apr': 'апреля',
        'May': 'мая',
        'Jun': 'июня',
        'Jul': 'июля',
        'Aug': 'августа',
        'Sep': 'сентября',
        'Oct': 'октября',
        'Nov': 'ноября',
        'Dec': 'декабря'
    }

    input_date = input_date[5:-9]

    # Split the input string
    date_parts = input_date.split()

    # Extract day, month, year, and time
    day = int(date_parts[0])
    month = month_names[date_parts[1]]
    year = int(date_parts[2])
    time = date_parts[3]

    # Format the output string
    output_date = f"{day} {month} {year} ({time})"
    return output_date


async def get_all_news():
    # Fetch the RSS feed with additional headers
    response = requests.get(RSS_FEED_URL, headers=headers, allow_redirects=True, verify=False)
    soup = BeautifulSoup(response.text, 'xml')

    # Extract information from all items in the feed
    items = soup.find_all('item')

    # Create a list to store the information for each item
    news_list = []

    for item in items:
        title = item.find('title').text
        description = item.find('description').text
        link = item.find('link').text
        image_url = item.find('enclosure')['url']
        date = convert_date(item.find('pubDate').text)
        guid = item.find('guid').text  # Add this line to get the news identifier

        # Save the information into a dictionary
        news_info = {
            'title': title,
            'description': description,
            'link': link,
            'image_url': image_url,
            'date': date,
            'guid': guid  # Add the news identifier to the dictionary
        }

        # Append the dictionary to the list
        news_list.append(news_info)

    return reversed(news_list)


async def send_news_to_telegram(news_list, sent_news_ids):
    # Send each news item to the Telegram chat if it hasn't been sent before
    bot = Bot(token=BOT_TOKEN)
    for news in news_list:
        photo_url = news['image_url']
        caption = f"<b>{news['title']}</b>\n\n{news['description']}\n\n{news['date']}\n\n<a href=\"{news['link']}\">Читать подробнее</a>"

        # Check if the news has already been sent
        if news['guid'] not in sent_news_ids:
            # Download the image and save it locally
            image_filename = await download_image(photo_url, news['guid'])

            # Send the photo from the local file
            with open(image_filename, 'rb') as photo_file:
                await bot.send_photo(chat_id=CHAT_ID, photo=photo_file, caption=caption, parse_mode='HTML')

                # Close the temporary image file explicitly
                photo_file.close()

                # Remove the temporary image file
                os.remove(image_filename)

                # Record the sent news identifier
                with open('sent_news.txt', 'a') as file:
                    file.write(news['guid'] + '\n')

            print("Wait 3 secs before sending the next message")
            time.sleep(3)


# Use asyncio to run the asynchronous functions
async def main():
    while True:
        try:
            # Read the list of previously sent news identifiers
            with open('sent_news.txt', 'r') as file:
                sent_news_ids = set(line.strip() for line in file)

            news_list = await get_all_news()
            await send_news_to_telegram(news_list, sent_news_ids)

            # Set the interval to wait before checking for new updates (in seconds)
            interval = 60
            print(f"Waiting for {interval} seconds before checking for updates...")
            await asyncio.sleep(interval)

        except Exception as e:
            print(f"An error occurred: {e}")
            logging.error(e)
            # logging.error(traceback.format_exc())
            print('Waiting 10 secs before next attempt')
            await asyncio.sleep(10)
            print("Restarting the program...")
            continue


# Run the asyncio event loop
if __name__ == "__main__":
    asyncio.run(main())
