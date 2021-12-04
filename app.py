import re

from flask import Flask, render_template, request, abort, redirect
import json

app = Flask(__name__)


#
# Фильтры для шаблонизатора
#

@app.template_filter()
def comment_beautifier(comment_count):
    """
    По переданному количеству комментариев возвращает правильное окончание

    :param comment_count: Количество комментариев
    :return: Строка с правильным окончанием слова "комментарий" для числа
    """
    remainder = comment_count % 10
    if comment_count == 0:
        return "Нет комментариев"
    elif (comment_count in range(11, 20)) or (remainder in range(5, 10)) or (remainder == 0):
        return "{} комментариев".format(comment_count)
    elif remainder in range(2, 5):
        return "{} комментария".format(comment_count)
    elif remainder == 1:
        return "{} комментарий".format(comment_count)


@app.template_filter()
def is_post_in_bookmarks(postid):
    """
    Проверка на наличие поста в закладках. Фильтр для шаблонизатора
    :param postid: id поста
    :return: True - если есть в базе, False - если нет
    """
    with open('data/bookmarks.json', 'r', encoding='utf-8') as bookmarks:
        return False if next(filter(lambda x: x['id'] == postid, json.load(bookmarks)),
                             None) is None else True


#
# Всопомгательные функции, работа с данными
#

# Получение поста из базы по Id
def get_post_by_id(postid):
    with open('data/data.json', 'r', encoding='utf-8') as data_file:
        post = next(filter(lambda x: x['pk'] == postid, json.load(data_file)), None)
    return post

# Получение комментариев, относящихся к посту с id = postid
def get_comments_by_post(postid):
    with open('data/comments.json', 'r', encoding='utf-8') as fp:
        comments_to_post = list(filter(lambda x: x['post_id'] == postid, json.load(fp)))
    return comments_to_post


def get_posts_with_comments_count(filter_func=(lambda _: True)):
    """
    Дописывает кол-во комментариев для найденных(или всех) постов

    :param filter_func: функция фильтрации. По дефолту вернёт все посты.
    :return: Возвращает список постов
    """
    with open('data/data.json', 'r', encoding='utf-8') as data_file:
        filtered_posts = list(filter(filter_func, json.load(data_file)))
    with open('data/comments.json', 'r', encoding='utf-8') as data_file:
        all_comments = json.load(data_file)
        for post in filtered_posts:
            comments_count = len(list(filter(lambda x: x['post_id'] == post['pk'], all_comments)))
            post['comments_count'] = comments_count
    return filtered_posts

# Добавление поста в базу закладок
def add_post_to_bookmarks(postid):
    with open('data/bookmarks.json', 'r', encoding='utf-8') as bookmarks:
        data = json.load(bookmarks)
    if {'id': postid} not in data:
        data.append({'id': postid})
    with open('data/bookmarks.json', 'w', encoding='utf-8') as bookmarks:
        json.dump(data, bookmarks)

# Удаление поста из базы закладок
def delete_post_from_bookmarks(postid):
    with open('data/bookmarks.json', 'r', encoding='utf-8') as bookmarks:
        data = json.load(bookmarks)
    if {'id': postid} in data:
        data.remove({'id': postid})
    with open('data/bookmarks.json', 'w', encoding='utf-8') as bookmarks:
        json.dump(data, bookmarks)


# Получение списка постов, добавленных в закладки
def get_posts_by_bookmarks():
    with open('data/bookmarks.json', 'r', encoding='utf-8') as bookmarks:
        data = json.load(bookmarks)
        return get_posts_with_comments_count(lambda post: {"id": post['pk']} in data)


# Получение кол-ва закладок для отображения на главной
def get_bookmarks_count():
    with open('data/bookmarks.json', 'r', encoding='utf-8') as bookmarks:
        return len(json.load(bookmarks))


def add_comment_to_post(postid, commenter_name, comment):
    """
    Добавление комментария в базу (json-файл)

    :param postid: id поста к которому добавляется комментарий
    :param commenter_name: имя пользователя, оставляющего комментарий
    :param comment: текст комментария
    :return: Результатом работы будет добавленная запись в файл comments.json
    """
    with open('data/comments.json', 'r', encoding='utf-8') as comments:
        data = json.load(comments)
        # Вычисление нового индекса как максимальный из имеющихся +1
        new_pk = max(data, key=lambda x: x['pk'])['pk'] + 1
    data.append({
        "post_id": postid,
        "commenter_name": commenter_name,
        "comment": comment,
        "pk": new_pk
    })
    with open('data/comments.json', 'w', encoding='utf-8') as comments:
        json.dump(data, comments)


#
#   Непосредственно представления
#

# Отображение списка всех постов для главной страницы
@app.route('/')
def index():
    return render_template('index.html', all_posts=get_posts_with_comments_count(),
                           bookmarks_count=get_bookmarks_count())


# Отображение одного поста с комментариями к нему
@app.route('/posts/<int:postid>')
def get_post(postid):
    if get_post_by_id(postid) is None:
        abort(404)
    post_with_tags = get_post_by_id(postid)
    post_with_tags['content'] = re.sub(
        pattern=r"#(\w*[а-яА-Я]*)",
        repl=lambda match_obj: '<a href=/tag/{0}>#{0}</a>'.format(match_obj.group(1)),
        string=post_with_tags['content']
    )
    return render_template('post.html', post=post_with_tags, comments=get_comments_by_post(postid))


# Отображение для поиска по вхождению слова в текст поста
@app.route('/search/')
def search_result():
    keyword = request.args.get('s')
    found_posts = get_posts_with_comments_count(
        lambda x: bool(re.search(keyword, x['content'], re.IGNORECASE)) if keyword is not None else True
    )
    return render_template('search.html', found_posts=found_posts)


# Отображение списка постов по автору
@app.route('/users/<username>')
def user_feed(username):
    # по хорошему, надо бы смотреть, есть ли такой юзер впринципе... Но, ладно, можно конечно
    # пройтись по Json с постами и посмотреть всех юзеров, но мб юзер такой есть, а постов нету...
    # Ну, хотя бы вывести заглушку, что постов нету, а не голую шапку. Таблицы с пользователями у нас нету((
    posts_by_user = get_posts_with_comments_count(lambda x: x['poster_name'] == username)
    return render_template('user-feed.html', posts_by_user=posts_by_user, username=username)


# Отображение списка постов по тегу
@app.route('/tag/<tagname>')
def posts_by_tag(tagname):
    posts_with_tag = get_posts_with_comments_count(
        lambda post: bool(re.search(pattern=r"#{}[^\\wа-яА-Я]?".format(tagname),
                                    string=post['content'],
                                    flags=re.IGNORECASE)
                          )
    )
    return render_template('tag.html', posts_with_tag=posts_with_tag, tag=tagname)

# Урл для добавления поста в закладки
@app.route('/bookmarks/add/<int:postid>')
def add_to_bookmarks(postid):
    add_post_to_bookmarks(postid)
    return redirect('/', code=302)

# Урл для удаление поста из закладкок
@app.route('/bookmarks/remove/<int:postid>')
def remove_from_bookmarks(postid):
    delete_post_from_bookmarks(postid)
    return redirect('/', code=302)

# Отображение для списка постов, добавленных в закладки
@app.route('/bookmarks')
def posts_in_bookmarks():
    return render_template('bookmarks.html', posts_in_bookmarks=get_posts_by_bookmarks())


# Почему бы не добавить примитивную обработку добавления коммента..
@app.route('/add_comment/<int:postid>')
def add_comment(postid):
    add_comment_to_post(
        postid=postid,
        commenter_name=request.args.get('username'),
        comment=request.args.get('content')
    )
    return redirect('/posts/{}'.format(postid), code=302)


#
#s
#

if __name__ == '__main__':
    app.run()
