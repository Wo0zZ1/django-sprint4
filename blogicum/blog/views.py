from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Comment, Post

User = get_user_model()

POSTS_PER_PAGE = 10


def get_posts():
    return Post.objects.select_related('author', 'category', 'location')


def filter_published(posts):
    return posts.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    )


def with_comment_count(posts):
    # После annotate порядок из Meta не применяется, поэтому задаём его явно
    return posts.annotate(
        comment_count=Count('comments')
    ).order_by(*Post._meta.ordering)


def get_page(request, posts):
    return Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get('page'))


def index(request):
    posts = with_comment_count(filter_published(get_posts()))
    return render(
        request, 'blog/index.html', {'page_obj': get_page(request, posts)}
    )


def post_detail(request, post_id):
    post = get_object_or_404(get_posts(), pk=post_id)
    # Автор видит свой пост, даже если он отложен или снят с публикации
    if post.author != request.user:
        post = get_object_or_404(filter_published(get_posts()), pk=post_id)
    context = {
        'post': post,
        'form': CommentForm(),
        'comments': post.comments.select_related('author'),
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    posts = with_comment_count(
        filter_published(get_posts()).filter(category=category)
    )
    context = {'category': category, 'page_obj': get_page(request, posts)}
    return render(request, 'blog/category.html', context)


def profile(request, username):
    profile = get_object_or_404(User, username=username)
    posts = get_posts().filter(author=profile)
    if profile != request.user:
        posts = filter_published(posts)
    context = {
        'profile': profile,
        'page_obj': get_page(request, with_comment_count(posts)),
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user.username)
    return render(request, 'blog/create.html', {'form': form})


def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id, author=request.user)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', request.user.username)
    context = {'form': PostForm(instance=post)}
    return render(request, 'blog/create.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(filter_published(Post.objects), pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id, author=request.user
    )
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    context = {'form': form, 'comment': comment}
    return render(request, 'blog/comment.html', context)


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id, author=request.user
    )
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
