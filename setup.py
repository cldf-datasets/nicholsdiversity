from setuptools import setup


setup(
    name='cldfbench_nicholsdiversity',
    py_modules=['cldfbench_nicholsdiversity'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'nicholsdiversity=cldfbench_nicholsdiversity:Dataset',
        ]
    },
    install_requires=[
        'cldfbench',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
